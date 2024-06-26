import pickle

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import redirect, render
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing.sequence import pad_sequences
from tensorflow.keras.preprocessing.text import Tokenizer
# from django.contrib.auth.forms import UserCreationForm
from .models import Room, Topic, Message, User
from .forms import RoomForm, UserForm, MyUserCreationForm

# Create your views here.

# rooms = [
#     {'id' : 1, 'name':'Texte 1'},
#     {'id' : 2, 'name':'Texte 2'},
#     {'id' : 3, 'name':'Texte 3'},
# ]

def loginPage(request):
    page = 'login'
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        email = request.POST.get('email').lower()
        password = request.POST.get('password')

        try:
            user = User.objects.get(email=email)
        except:
            messages.error(request, "L'utilisateur n'existe pas.")

        user = authenticate(request, email=email, password=password)

        if user is not None:
            login(request, user)
            return redirect('home')
        else:
            messages.error(request, "L'utilisateur ou le mot de passe est incorrect.")

    context = {'page':page}
    return render(request, 'pages/login_register.html', context)

def logoutUser(request):
    logout(request)
    return redirect('home')

def registerPage(request):
    form = MyUserCreationForm()

    if request.method == 'POST':
        form = MyUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.username = user.username.lower()
            user.save()
            login(request, user)
            return redirect('home')
        else:
            messages.error(request, "Une erreur s'est produite lors de la création du compte")

    return render(request, 'pages/login_register.html', {'form':form})

def home(request):
    q = request.GET.get('q') if request.GET.get('q') != None else ''

    rooms = Room.objects.filter(
        Q(topic__name__icontains=q) |
        Q(name__icontains=q) |
        Q(description__icontains=q)
    )

    topics = Topic.objects.all()[0:4]
    room_count = rooms.count()
    room_messages = Message.objects.filter(Q(room__topic__name__icontains=q))

    context = {'rooms': rooms, 'topics': topics, 'room_count': room_count, 'room_messages': room_messages}
    return render(request, 'pages/home.html', context )

# ce bout de code permet de charger le modèle avec pickle (en bref de l'ouvrir pour l'utiliser par la suite)
with open('C:\\Users\\Aika\\Documents\\cours aflokkat\\projet certif\\site projet\\projet feelflow\\feelflow\\naive_bayes_model.pkl', 'rb') as f1:
    model = pickle.load(f1)

with open('C:\\Users\\Aika\\Documents\\cours aflokkat\\projet certif\\site projet\\projet feelflow\\feelflow\\vectorizer.pkl', 'rb') as f2:
    vectorizer = pickle.load(f2)

def room(request, pk):
    room = Room.objects.get(id=pk)
    room_messages = room.message_set.all()
    participants = room.participants.all()

    if request.method == 'POST':
        # stext = abréviation de "search text", vu qu'on l'utilise pour l'analyse
        stext = request.POST.get('body')

        # vtext = sert a transformer le texte du message en vecteurs, d'ou son nom
        vtext = vectorizer.transform([stext])

        # définition des emotions ressortant du message
        emotion = model.predict(vtext)

        message = Message.objects.create(
            user=request.user,
            room=room,
            body=stext,
            # x = 1 if y > 0 else 0
            emotions='P' if emotion == 1 else 'N', # on ajoute ensuite le sentiment déterminé en dessous du message
        )

        room.participants.add(request.user)
        return redirect('room', pk=room.id)

    context = {'room': room, 'room_messages': room_messages, 'participants':participants}
    return render(request, 'pages/room.html', context)

def userProfile(request, pk):
    user = User.objects.get(id=pk)
    rooms = user.room_set.all()
    room_messages = user.message_set.all()
    topics = Topic.objects.all()
    context = {'user': user, 'rooms': rooms, 'room_messages':room_messages, 'topics':topics}
    return render(request, 'pages/profile.html', context)

@login_required(login_url='login')
def createRoom(request):
    form = RoomForm()
    topics = Topic.objects.all()

    if request.method == 'POST':
        topic_name = request.POST.get('topic')
        topic, created = Topic.objects.get_or_create(name=topic_name)

        Room.objects.create(
            host=request.user,
            topic=topic,
            name=request.POST.get('name'),
            description=request.POST.get('description'),
        )
        # anciennement utilisé (avant l'utilisation de Room.objets.create)
        # form = RoomForm(request.POST)
        # if form.is_valid():
        #     room = form.save(commit=False)
        #     room.host = request.user
        #     room.save()
        #     return redirect('home')
        return redirect('home')

    context = {'form': form, 'topics':topics}
    return render(request, 'pages/room_form.html', context)

@login_required(login_url='login')
def updateRoom(request, pk):
    room = Room.objects.get(id=pk)
    form = RoomForm(instance=room)
    topics = Topic.objects.all()

    if request.user != room.host:
        return HttpResponse("Vous n'avez pas accès à cette section du site!!")

    if request.method == 'POST':
        topic_name = request.POST.get('topic')
        topic, created = Topic.objects.get_or_create(name=topic_name)
        room.name = request.POST.get('name')
        room.topic = topic
        room.description = request.POST.get('description')
        room.save()
        # form = RoomForm(request.POST, instance=room)
        # if form.is_valid():
        #     form.save()
        #     return redirect('home')
        return redirect('home')

    context = {'form' : form, 'topics':topics, 'room':room}
    return render(request, 'pages/room_form.html', context)

@login_required(login_url='login')
def deleteRoom(request, pk):
    room = Room.objects.get(id=pk)

    if request.user != room.host:
        return HttpResponse('You are not allowed here!!')

    if request.method == 'POST':
        room.delete()
        return redirect('home')

    return render(request, "pages/delete.html", {'obj':room})

@login_required(login_url='login')
def deleteMessage(request, pk):
    message = Message.objects.get(id=pk)

    if request.user != message.user:
        return HttpResponse('You are not allowed here!!')

    if request.method == 'POST':
        message.delete()
        return redirect('home')

    return render(request, "pages/delete.html", {'obj':message})

@login_required(login_url='login')
def updateUser(request):
    user = request.user
    form = UserForm(instance=user)

    if request.method == 'POST':
        form = UserForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            form.save()
            return redirect('user-profile', pk=user.id)
    return render(request, 'pages/update-user.html', {'form':form})

def topicsPage(request):
    q = request.GET.get('q') if request.GET.get('q') != None else ''
    topics = Topic.objects.filter(name__icontains=q)
    return render(request, 'pages/topics.html',{'topics':topics})

def activityPage(request):
    room_messages = Message.objects.all()
    return render(request,'pages/activity.html',{'room_messages':room_messages})