from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout

# Create your views here.

def index(request):
    return render(request, 'authentification/index.html')

def signup(request):
    if request.method == 'POST':
        #username = request.POST.get('username')
        username = request.POST['username']
        fname = request.POST['fname']
        sname = request.POST['sname']
        email = request.POST['email']
        password1 = request.POST['password1']
        password2 = request.POST['password2']

        if User.objects.filter(username=username):
            messages.error(request, "Username already exist! Please try some other username.")
            return redirect('index')
        
        if User.objects.filter(email=email).exists():
            messages.error(request, "Email Already Registered!!")
            return redirect('index')
        
        if len(username)>25:
            messages.error(request, "Username must be under 20 charcters!!")
            return redirect('index')
        
        if password1 != password2:
            messages.error(request, "Passwords didn't matched!!")
            return redirect('index')
        
        if not username.isalnum():
            messages.error(request, "Username must be Alpha-Numeric!!")
            return redirect('index')

        newUser = User.objects.create_user(username, email, password1)
        newUser.first_name = fname
        newUser.last_name = sname
        newUser.save()

        messages.success(request, 'your account created')
        return redirect('signin')

    return render(request, 'authentification/signup.html')

def signin(request):
    if request.method == 'POST':
        username = request.POST['username']
        password1 = request.POST['password1']

        user = authenticate(username=username,password= password1)
        if user is not None:
            login(request, user)
            fname = user.first_name
            return render(request,'authentification/index.html', {'fname': fname})
        else:
            messages.error(request, 'Wrong credentials')
            return redirect('index')
    return render(request, 'authentification/signin.html')

def signout(request):
    logout(request)
    messages.success(request,'Logged out')
    return redirect('index')