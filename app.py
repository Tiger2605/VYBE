import os
from werkzeug.utils import secure_filename
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)

# --- CONFIGURATION SÉCURISÉE ---
# On utilise une clé secrète dynamique pour plus de sécurité
app.secret_key = os.environ.get('SECRET_KEY', 'vybe_africa_secret_key_2026')

# Configuration de l'upload
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'mp4', 'mov', 'avi', 'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- CONFIGURATION DE LA BASE DE DONNÉES (HYBRIDE) ---
# Si on est sur Render, DATABASE_URL sera remplie. Sinon, on utilise SQLite.
database_url = os.environ.get('DATABASE_URL')

if database_url:
    # Correction pour SQLAlchemy : il faut absolument 'postgresql://' (avec un L)
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
else:
    # Ton fichier local pour travailler sans connexion internet
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///vibe_africa.db'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# ---------------------------------------------------------
# LE RESTE DE TES MODÈLES (User, Group, Video...) RESTE IDENTIQUE
# ---------------------------------------------------------

# Table d'association pour les followers
followers = db.Table('followers',
    db.Column('follower_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('followed_id', db.Integer, db.ForeignKey('user.id'))
)

# NOUVEAU : Table d'association pour les membres d'un groupe (Communauté)
group_members = db.Table('group_members',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('group_id', db.Integer, db.ForeignKey('group.id'))
)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    bio = db.Column(db.String(200), default="Salut, je suis sur VIBE AFRICA !")
    google_id = db.Column(db.String(100), unique=True, nullable=True)
    phone = db.Column(db.String(20), nullable=True) # NOUVEAU : Numéro de téléphone pour les contacts

    Video = db.relationship('Video', backref='author', lazy=True)

    # Relation Followers
    following = db.relationship(
        'User', secondary=followers,
        primaryjoin=(followers.c.follower_id == id),
        secondaryjoin=(followers.c.followed_id == id),
        backref=db.backref('followers', lazy='dynamic'), lazy='dynamic'
    )

# NOUVEAU : Modèle pour les Communautés/Groupes
class Group(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255))
    creator_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Lien avec les membres
    members = db.relationship('User', secondary=group_members, backref=db.backref('groups', lazy='dynamic'))

# NOUVEAU : Messages envoyés dans les groupes
class GroupMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'))
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class Like(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    video_id = db.Column(db.Integer, db.ForeignKey('video.id'))

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
    filename = db.Column(db.String(100))
    category = db.Column(db.String(50), nullable=False, default='Autres')
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    likes = db.relationship('Like', backref='video', lazy=True)
    views = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)


# --- ROUTES ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        phone = request.form.get('phone') # NOUVEAU : Récupération du téléphone si fourni
        
        new_user = User(username=username, password=password, phone=phone)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.password == password:
            session['user_id'] = user.id 
            session['username'] = user.username
            return redirect(url_for('dashboard'))
        else:
            # On utilise flash pour envoyer le message d'erreur
            flash("Identifiants incorrects. Veuillez réessayer.", "error")
            return redirect(url_for('login')) # On recharge la page de login
            
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    selected_category = request.args.get('category')
    search_query = request.args.get('q') 
    query = Video.query
    
    if selected_category:
        query = query.filter_by(category=selected_category)
        
    if search_query:
        query = query.filter(Video.title.ilike(f"%{search_query}%"))
        
    videos = query.order_by(Video.created_at.desc()).all()
    
    def get_pending_requests():
        requests = FriendRequest.query.filter_by(receiver_id=session['user_id'], status='pending').all()
        for req in requests:
            sender = User.query.get(req.sender_id)
            if sender:
                req.sender_name = sender.username
        return requests
            
    return render_template('dashboard.html', 
                           videos=videos, 
                           get_pending_requests=get_pending_requests,
                           selected_category=selected_category,
                           search_query=search_query)

@app.route('/logout')
def logout():
    session.clear()
    flash("Vous avez été déconnecté.", "success")
    return redirect(url_for('login'))

@app.route('/profile/')
@app.route('/profile/<username>')
def profile(username=None):
    # CAS 1 : L'utilisateur n'est pas connecté et n'a pas spécifié de nom (clic sur icône Profil)
    if username is None and 'user_id' not in session:
        return render_template('profile_guest.html')

    # CAS 2 : L'utilisateur est connecté et clique sur son propre profil (via la barre de tâche)
    if username is None and 'user_id' in session:
        username = session['username']
    
    # Récupération de l'utilisateur ou erreur 404 si le nom n'existe pas
    user = User.query.filter_by(username=username).first_or_404()
    
    # Récupération des publications (Vibes) de cet utilisateur
    vibes = Video.query.filter_by(user_id=user.id).order_by(Video.created_at.desc()).all()
    
    me = None
    friendship = None
    is_own_profile = False
    
    if 'user_id' in session:
        me = User.query.get(session['user_id'])
        # Vérification si l'utilisateur regarde son propre profil
        if me.id == user.id:
            is_own_profile = True
        
        # Vérification du statut d'amitié
        friendship = FriendRequest.query.filter(
            (((FriendRequest.sender_id == me.id) & (FriendRequest.receiver_id == user.id)) |
             ((FriendRequest.sender_id == user.id) & (FriendRequest.receiver_id == me.id))),
            FriendRequest.status == 'accepted'
        ).first()
        
    return render_template('profile.html', 
                           user=user, 
                           current_user_obj=me, 
                           friendship=friendship, 
                           vibes=vibes, 
                           is_own_profile=is_own_profile)

@app.route('/follow/<username>')
def follow(username):
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    user_to_follow = User.query.filter_by(username=username).first_or_404()
    me = User.query.get(session['user_id'])
    
    if user_to_follow != me:
        if user_to_follow in me.following:
            me.following.remove(user_to_follow) 
        else:
            me.following.append(user_to_follow) 
        db.session.commit()
    
    return redirect(url_for('profile', username=username))

@app.route('/add_friend/<int:receiver_id>')
def add_friend(receiver_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    sender_id = session['user_id']
    existing_request = FriendRequest.query.filter_by(sender_id=sender_id, receiver_id=receiver_id).first()
    
    if not existing_request and sender_id != receiver_id:
        new_request = FriendRequest(sender_id=sender_id, receiver_id=receiver_id)
        db.session.add(new_request)
        db.session.commit()
        flash("Demande d'ami envoyée avec succès !", "success") 
    else:
        flash("Demande déjà envoyée ou impossible.", "error") 
    
    return redirect(url_for('dashboard'))

@app.route('/upload', methods=['GET', 'POST'])
def upload_video():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        if 'file' not in request.files:
            return "Pas de fichier détecté"
        
        file = request.files['file']
        title = request.form.get('title')
        category = request.form.get('category') 
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            
            new_video = Video(title=title, filename=filename, user_id=session['user_id'], category=category)
            db.session.add(new_video)
            db.session.commit()
            return redirect(url_for('dashboard'))
            
    return render_template('upload.html')

@app.route('/like/<int:video_id>')
def like_video(video_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    existing_like = Like.query.filter_by(user_id=session['user_id'], video_id=video_id).first()
    
    if existing_like:
        db.session.delete(existing_like) 
    else:
        new_like = Like(user_id=session['user_id'], video_id=video_id)
        db.session.add(new_like) 
        
    db.session.commit()
    return redirect(url_for('dashboard'))

@app.route('/comment/<int:video_id>', methods=['POST'])
def add_comment(video_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    content = request.form.get('content')
    if content:
        new_comment = Comment(content=content, user_id=session['user_id'], video_id=video_id)
        db.session.add(new_comment)
        db.session.commit()
        flash("Commentaire ajouté !", "success")
    
    return redirect(url_for('dashboard'))

@app.route('/increment_view/<int:video_id>', methods=['POST'])
def increment_view(video_id):
    video = Video.query.get_or_404(video_id)
    video.views += 1
    db.session.commit()
    return {'status': 'success', 'new_views': video.views}, 200

@app.route('/accept_friend/<int:request_id>')
def accept_friend(request_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    friend_req = FriendRequest.query.get_or_404(request_id)
    if friend_req.receiver_id == session['user_id']:
        friend_req.status = 'accepted'
        db.session.commit()
        flash("Demande acceptée ! Vous êtes maintenant amis. 🤝", "success")
        return redirect(url_for('dashboard'))
        
    flash("Action non autorisée.", "error")
    return redirect(url_for('dashboard'))

@app.route('/chat/<int:friend_id>', methods=['GET', 'POST'])
def chat(friend_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    me_id = session['user_id']
    friend = User.query.get_or_404(friend_id)
    
    is_friend = FriendRequest.query.filter(
        ((FriendRequest.sender_id == me_id) & (FriendRequest.receiver_id == friend_id) & (FriendRequest.status == 'accepted')) |
        ((FriendRequest.sender_id == friend_id) & (FriendRequest.receiver_id == me_id) & (FriendRequest.status == 'accepted'))
    ).first()
    
    if not is_friend:
        return "Vous devez être amis pour discuter. <a href='/dashboard'>Retour</a>"

    if request.method == 'POST':
        content = request.form.get('content')
        if content:
            new_msg = Message(sender_id=me_id, receiver_id=friend_id, content=content)
            db.session.add(new_msg)
            db.session.commit()
            return redirect(url_for('chat', friend_id=friend_id))

    messages = Message.query.filter(
        ((Message.sender_id == me_id) & (Message.receiver_id == friend_id)) |
        ((Message.sender_id == friend_id) & (Message.receiver_id == me_id))
    ).order_by(Message.timestamp.asc()).all()
    
    return render_template('chat.html', messages=messages, friend=friend)

# --- NOUVEAU : LISTE DES DISCUSSIONS ET COMMUNAUTÉS ---
@app.route('/messages')
def messages_list():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    me_id = session['user_id']
    me = User.query.get(me_id)
    
    # 1. Récupération des Amis (Privé)
    friends_relations = FriendRequest.query.filter(
        ((FriendRequest.sender_id == me_id) | (FriendRequest.receiver_id == me_id)),
        FriendRequest.status == 'accepted'
    ).all()
    
    friends = []
    for rel in friends_relations:
        friend_id = rel.receiver_id if rel.sender_id == me_id else rel.sender_id
        friend_user = User.query.get(friend_id)
        friends.append(friend_user)
        
    # 2. Récupération des Communautés (Groupes dont je suis membre)
    my_groups = me.groups.all()
        
    # On envoie les friends ET les groups au template HTML
    return render_template('messages_list.html', friends=friends, groups=my_groups)

# --- NOUVEAU : CRÉER UN GROUPE (POUR TON BOUTON +) ---
@app.route('/create_group', methods=['POST'])
def create_group():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    group_name = request.form.get('name')
    if group_name:
        me = User.query.get(session['user_id'])
        new_group = Group(name=group_name, creator_id=me.id)
        new_group.members.append(me) # On ajoute le créateur comme premier membre
        db.session.add(new_group)
        db.session.commit()
        flash("Communauté créée avec succès !", "success")
        
    return redirect(url_for('messages_list'))


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)