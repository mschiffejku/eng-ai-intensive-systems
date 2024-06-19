from django import forms


class UploadFileForm(forms.Form):
    file = forms.ImageField(label='Image')

# class CheckForm(forms.Form):
#     numberProducts = forms.TextInput(label='number')
    