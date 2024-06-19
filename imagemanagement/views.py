import math
from ast import Import
import os
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import redirect, render
from django.contrib import messages
from django.contrib.auth.decorators import login_required
import datetime


from imagemanagement.forms import UploadFileForm
#from imagemanagement.models import Uploadfiles

# BEGIN: add imports for YOLO
import json
import cv2
from ultralytics import YOLO
import supervision as sv
import numpy as np
# END: add imports for YOLO

context = {'image': None, 'number': None}
# Create your views here.
def handle_uploaded_file(doc):
    with open(f"uploads/{doc.name}", "wb+") as destination:
        #f.name
        #{user.username}_{datetime.date.today()} и расширение файла
        for chunk in doc.chunks():
            destination.write(chunk)
    return destination.name

def auto_canny(image, sigma=0.33):
    """automatically adjusted canny edge detection"""
    # compute the median of the single channel pixel intensities
    v = np.median(image)
    # apply automatic Canny edge detection using the computed median
    lower = int(max(0, (1.0 - sigma) * v))
    upper = int(min(255, (1.0 + sigma) * v))
    edged = cv2.Canny(image, lower, upper)
    # return the edged image
    return edged

def distance(p1, p2):
    """p1 and p2 in format (x1,y1) and (x2,y2) tuples"""
    dis = ((p2[0] - p1[0]) ** 2 + (p2[1] - p1[1]) ** 2) ** 0.5
    return dis

def process_image_with_ai(
        input_file
):
    input_fname_wodir = input_file.replace("uploads/", "")

    model = YOLO("imagemanagement/yolo/best-soda-can-again-with-amir.pt")

    # load image
    frame = cv2.imread(input_file)
    input_img_height, input_img_width, input_image_colors = frame.shape[:3]

    gray = cv2.cvtColor(frame.copy(), cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
    edges = auto_canny(blurred)

    # =====================================
    # BEGIN: MODEL #1: shelf area detection
    # =====================================
    lsd = cv2.createLineSegmentDetector(0)
    lines = lsd.detect(blurred)[0]

    horizontal_lines = []
    horizontal_slope = []
    horizontal_lines_ic = []
    vertical_lines = []
    vertical_slope = []
    vertical_lines_ic = []
    for line in lines:
        for x1, y1, x2, y2 in line:
            xdiff = x2 - x1
            if (xdiff == 0):
                xdiff = 0.000001
            slope = (y2 - y1) / xdiff  # <-- Calculating the slope.
            ic_y = y1 - (x1 * slope)

            if math.fabs(slope) < 0.1:  # <-- Only consider extreme slope
                if distance(
                        (x1, y1),
                        (x2, y2)
                ) > 100:
                    horizontal_lines.append(line)
                    horizontal_slope.append(slope)
                    horizontal_lines_ic.append(ic_y)
            if math.fabs(slope) > 3:
                if distance(
                        (x1, y1),
                        (x2, y2)
                ) > 100:
                    vertical_lines.append(line)
                    vertical_slope.append(slope)
                    vertical_lines_ic.append((x1 + x2) / 2)

    h = np.array(horizontal_lines_ic, dtype=np.float32)
    h_argmax = np.argmax(h, axis=0)
    h_argmin = np.argmin(h, axis=0)
    h_maxline = horizontal_lines[h_argmax]
    h_minline = horizontal_lines[h_argmin]

    v = np.array(vertical_lines_ic, dtype=np.float32)
    v_argmax = np.argmax(v, axis=0)
    v_argmin = np.argmin(v, axis=0)

    shelf_y_max = int(horizontal_lines_ic[h_argmax])
    shelf_y_min = int(horizontal_lines_ic[h_argmin])
    shelf_x_max = int(vertical_lines_ic[v_argmax])
    shelf_x_min = int(vertical_lines_ic[v_argmin])

    image_width = frame.shape[1]
    image_height = frame.shape[0]

    if shelf_y_max > image_height:
        shelf_y_max = image_height
    if shelf_y_min < 0:
        shelf_y_min = 0

    # ===================================
    # END: MODEL #1: shelf area detection
    # ===================================

    # =================================================
    # BEGIN: MODEL #2: products in shelf area detection
    # =================================================
    result = model(frame, agnostic_nms=True, conf=0.8)[0]
    detections = sv.Detections.from_ultralytics(result)
    labels = [
        f"{model.model.names[class_id]} {confidence:0.2f}"
        for _, _, confidence, class_id, _, _
        in detections
    ]
    classes = []
    cv2.rectangle(frame, (shelf_x_min, shelf_y_min), (shelf_x_max, shelf_y_max), color=(0, 255, 255),
                  thickness=5)

    # ===============================================
    # END: MODEL #2: products in shelf area detection
    # ===============================================

    # =========================================
    # BEGIN: result image + message compilation
    # =========================================
    result_fname = input_file.replace("uploads", "results")
    result_fname_wodir = result_fname.replace("results/", "")
    #context["image"] = result_fname_wodir

    detected_products = []
    global_min_x = 0
    global_min_y = 0
    global_max_x = 0
    global_max_y = 0
    for detection_index, detection in enumerate(detections):

        x1 = int(detection[0][0])
        y1 = int(detection[0][3])
        x2 = int(detection[0][2])
        y2 = int(detection[0][1])

        if (
                (x1 <= shelf_x_max and x1 >= shelf_x_min) and
                (x2 <= shelf_x_max and x2 >= shelf_x_min) and
                (y1 <= shelf_y_max and y1 >= shelf_y_min) and
                (y2 <= shelf_y_max and y2 >= shelf_y_min)
        ):

            print("###", detection_index, detection)

            p_ra = {
                # "rectangle_area": {
                "left_top": {
                    "x": int(detection[0][0]),
                    "y": int(detection[0][3])
                },
                "right_bottom": {
                    "x": int(detection[0][2]),
                    "y": int(detection[0][1])
                }
                # }
            }
            if int(detection[0][0]) < global_min_x:
                global_min_x = int(detection[0][0])
            if int(detection[0][2]) > global_max_x:
                global_max_x = int(detection[0][2])
            if int(detection[0][1]) < global_min_y:
                global_min_y = int(detection[0][1])
            if int(detection[0][3]) > global_max_y:
                global_max_y = int(detection[0][3])

            p = {
                "product_code": model.model.names[detection[3]],
                "confidence": int(detection[2] * 100),
                "rectangle_area": p_ra
            }

            detected_products.append(p)

            # For bounding box
            color_rectangle = (0, 255, 0)
            color_text = (0, 0, 0)
            img = cv2.rectangle(frame, (x1, y1), (x2, y2), color_rectangle, thickness=2)

            # For the text background
            # Finds space required by the text so that we can put a background with that amount of width.
            (w, h), _ = cv2.getTextSize(
                labels[detection_index], cv2.FONT_HERSHEY_SIMPLEX, 0.6, 1)

            # Prints the text.
            img = cv2.rectangle(frame, (x1, y1 - 20), (x1 + w, y1), color_rectangle, -1)
            img = cv2.putText(frame, labels[detection_index], (x1, y1 - 5),
                              cv2.FONT_HERSHEY_SIMPLEX, 0.6, color_text, thickness=1)

    shelf_ra = {
        "left_top": {
            "x": shelf_x_min,
            "y": shelf_y_max
        },
        "right_bottom": {
            "x": shelf_x_max,
            "y": shelf_y_min
        }
    }
    scan_result = {
        "shelf_scan_result": {
            "shelf": {
                "rectangle_area": shelf_ra
            },
            "products": detected_products,
            "original_image": input_fname_wodir,
            "result_image": result_fname_wodir
        }
    }

    scan_result_json = json.dumps(scan_result)
    json_fname = result_fname.replace("jpg", "json")
    with open(json_fname, "w") as outfile:
        outfile.write(scan_result_json)

    cv2.imwrite(result_fname, frame)

    # load results from JSON
    with open(json_fname) as f:
        result_details = json.load(f)
        result_image_name = result_details['shelf_scan_result']['result_image']
        result_detected_shelf = result_details['shelf_scan_result']['shelf']
        result_detected_products_on_shelf = result_details['shelf_scan_result']['products']

    # =======================================
    # END: result image + message compilation
    # =======================================
    #result_checkredirect = result_checkredirect(HttpResponseRedirect('resultchecking'), result_image_name, json)
    # return tuple from JSON that you got from AI result
    result_dict = dict()
    result_dict['shelf'] = result_detected_shelf
    result_dict['products'] = result_detected_products_on_shelf
    result_dict['resulting_image'] = result_image_name

    return result_dict

@login_required
def mockwhms(request):
    #could be copy json file from result to whms folder as example of 
    message = messages.success(request, 'Data is send to WHMS')
    return render(request, 'imagemanagement/mockwhms.html')

@login_required
def resultcheck(request):
    global context
    # if request.method == "POST":
    #     form = CheckForm(request.POST, initial=context['number'])
    #     #handle_uploaded_file(request.FILES['image'])
    #     if form.is_valid():
    #         pass
    #         #save updated dictionary/ json file
    #         mockwhms(request)

    return render(request, 'imagemanagement/result.html', context)
    #return render(request, 'imagemanagement/result.html',{'form':form})


@login_required
def start(request):
    if request.method == "POST":
        form = UploadFileForm(request.POST, request.FILES)
        #handle_uploaded_file(request.FILES['image'])
        if form.is_valid():
            # fp = Uploadfiles(form.cleaned_data  ['file'], request.user.username)
            # fp.save()
            #currentuser = request.user
            input_file = handle_uploaded_file(form.cleaned_data['file'])

            # call AI
            result_dict = process_image_with_ai(input_file)

            # resulting annotated image
            result_fname = result_dict['resulting_image']
            # shelf area
            shelf = result_dict['products']
            # count number of products
            no_of_prods = len(result_dict['products'])
            
            message_str = "image uploaded and scanned => " + str(no_of_prods) + " products found on shelf"
            context["image"] = result_dict['resulting_image']
            context["number"] = no_of_prods
            #test = 99
            #recording file in chunks
            #resultcheck(request, { 'image': input_file, 'number' :no_of_prods })
            messages.success(request, message_str)
            #redirect('/resultcheck')
            
            #render(request, 'imagemanagement/result.html', { 'image': input_file, 'number' :no_of_prods })
            

    else:
        form = UploadFileForm()
    return render(request, 'imagemanagement/start.html',{'form':form})

