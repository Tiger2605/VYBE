from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

from sqlalchemy import Boolean

# 1. On initialise l'objet db, MAIS sans l'attacher à l'application tout de suite.
db = SQLAlchemy()

# ---------------------------------------------------------
# TABLES D'ASSOCIATION
# ---------------------------------------------------------
followers = db.Table('followers',
    db.Column('follower_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('followed_id', db.Integer, db.ForeignKey('user.id'))
)

group_members = db.Table('group_members',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('group_id', db.Integer, db.ForeignKey('group.id'))
)

# ---------------------------------------------------------
# MODÈLES DE DONNÉES
# ---------------------------------------------------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    bio = db.Column(db.String(200), default="Salut, je suis sur VIBE AFRICA !")
    profile_pic = db.Column(db.String(255), default='default_profile.png') # AJOUT : Photo de profil
    google_id = db.Column(db.String(100), unique=True, nullable=True)
    phone = db.Column(db.String(20), nullable=True)

    Video = db.relationship('Video', backref='author', lazy=True)
    following = db.relationship(
        'User', secondary=followers,
        primaryjoin=(followers.c.follower_id == id),
        secondaryjoin=(followers.c.followed_id == id),
        backref=db.backref('followers', lazy='dynamic'), lazy='dynamic'
    )
    
    # AJOUT : Relation pour les favoris
    favorites = db.relationship('Favorite', backref='user', lazy='dynamic')

class Group(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255))
    creator_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    members = db.relationship('User', secondary=group_members, backref=db.backref('groups', lazy='dynamic'))

class GroupMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'))
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    # CORRECTION ICI : nullable=False doit être dans db.Column
    content = db.Column(db.Text, nullable=False) 
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class Like(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    video_id = db.Column(db.Integer, db.ForeignKey('video.id'))

# AJOUT : Modèle pour enregistrer les vidéos en favoris
class Favorite(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    video_id = db.Column(db.Integer, db.ForeignKey('video.id'))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    video_id = db.Column(db.Integer, db.ForeignKey('video.id'), nullable=False)
    author = db.relationship('User', backref='comments')

class FriendRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    status = db.Column(db.String(20), default='pending') 

class Video(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100))
    filename = db.Column(db.String(500), nullable=False)
    category = db.Column(db.String(50), nullable=False, default='Autres')
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    likes = db.relationship('Like', backref='video', lazy=True)
    favs = db.relationship('Favorite', backref='video', lazy=True) # AJOUT : Lien Video -> Favoris
    views = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class AppUpdate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100))
    message = db.Column(db.Text)
    date = db.Column(db.DateTime, default=datetime.utcnow)

class Business(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False) # boutique, ecole, etc.
    description = db.Column(db.Text)
    location = db.Column(db.String(255))
    contact = db.Column(db.String(100))
    image_url = db.Column(db.String(255), default="default_biz.png")
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    owner = db.relationship('User', backref=db.backref('businesses', lazy=True))

    # CORRECTION ICI : Ajout de db. devant Boolean
    is_certified = db.Column(db.Boolean, default=False)
    is_secured = db.Column(db.Boolean, default=True)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text)
    stock = db.Column(db.Integer, default=1)
    # Spécificités Mode
    sizes = db.Column(db.String(100))  # Ex: "S, M, L, XL"
    colors = db.Column(db.String(100)) # Ex: "Noir, Bleu, Blanc"
    material = db.Column(db.String(100)) # Ex: "Coton, Lin"
    condition = db.Column(db.String(50)) # Ex: "Neuf, Occasion"
    
    # Gestion des images (Multi-photos)
    image_main = db.Column(db.String(255))
    image_alt = db.Column(db.Text) # URLs séparées par des virgules
    
    business_id = db.Column(db.Integer, db.ForeignKey('business.id'), nullable=False)