import re
import os
from sqlalchemy import text
from flask_migrate import Migrate
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, render_template, request, redirect, url_for, session, flash
from models import db, User, Group, GroupMessage, Like, Comment, FriendRequest, Video,Favorite, Message as MessageModel, AppUpdate
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from itsdangerous import URLSafeTimedSerializer
from flask_mail import Mail, Message as MailMessage
import cloudinary
import cloudinary.uploader
import cloudinary.api

# 1. CRÉATION DE L'APPLICATION
app = Flask(__name__)

# 2. CONFIGURATION DE LA CLÉ SECRÈTE
app.secret_key = os.environ.get('SECRET_KEY', 'vybe_africa_secret_key_2026')

# --- CONFIGURATION DE LA BASE DE DONNÉES ---
database_url = os.environ.get('DATABASE_URL')

if not database_url:
    if os.environ.get('RENDER'):
        raise RuntimeError("❌ DATABASE_URL manquante sur Render. Vérifie l'onglet Environment !")
    else:
        # SQLite local pour le développement
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///vibe_africa.db'
else:
    # Correction pour SQLAlchemy 2.0 (postgres:// -> postgresql://)
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# 3. INITIALISATION DES EXTENSIONS (Le bloc demandé)
db.init_app(app)
migrate = Migrate(app, db)  # Flask-Migrate est maintenant bien lié
s = URLSafeTimedSerializer(app.secret_key)

# --- CONFIGURATION EMAIL ---
app.config.update(
    MAIL_SERVER='smtp.gmail.com',
    MAIL_PORT=587,
    MAIL_USE_TLS=True,
    MAIL_USERNAME=os.environ.get('MAIL_USER'),
    MAIL_PASSWORD=os.environ.get('MAIL_PASS'),
    MAIL_DEFAULT_SENDER=os.environ.get('MAIL_USER')
)
mail = Mail(app)

# --- CONFIGURATION CLOUDINARY ---
cloudinary.config(
    cloud_name=os.environ.get('CLOUDINARY_CLOUD_NAME'),
    api_key=os.environ.get('CLOUDINARY_API_KEY'),
    api_secret=os.environ.get('CLOUDINARY_API_SECRET')
)

# --- CONFIGURATION DE LIMITEUR (RATE LIMITER) ---
limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=["300 per day", "100 per hour"],
    storage_uri="memory://"
)

# --- CONFIGURATION DE L'UPLOAD ---
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'mp4', 'mov', 'avi', 'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Dossier spécifique pour les photos de profil
UPLOAD_FOLDER_PROFILES = os.path.join(app.config['UPLOAD_FOLDER'], 'profiles')
if not os.path.exists(UPLOAD_FOLDER_PROFILES):
    os.makedirs(UPLOAD_FOLDER_PROFILES)

# --- ROUTES ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # 1. On récupère TOUTES les données du formulaire
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        email = request.form.get('email', '').strip()  # <--- AJOUTÉ
        phone = request.form.get('phone', '').strip()
        bio = request.form.get('bio', '').strip()      # <--- AJOUTÉ
        
        # 2. On vérifie que les champs obligatoires sont là
        if not username or not password or not phone or not email:
            flash("Erreur : Tous les champs (incluant l'email) doivent être remplis.", "error")
            return redirect(url_for('register'))

        # Validations RegEx (Username et Téléphone)
        if not re.match(r"^[a-zA-Z0-9_]{3,20}$", username):
            flash("Nom d'utilisateur invalide.", "error")
            return redirect(url_for('register'))

        if not re.match(r"^0[89][0-9]{8}$", phone):
            flash("Format de numéro invalide (10 chiffres commençant par 08 ou 09).", "error")
            return redirect(url_for('register'))

        # 3. Vérifier si l'utilisateur existe déjà
        user_exists = User.query.filter((User.username == username) | (User.email == email)).first()
        if user_exists:
            flash("Le nom d'utilisateur ou l'email est déjà utilisé.", "error")
            return redirect(url_for('register'))

        # 4. Hachage et création de l'utilisateur
        hashed_pw = generate_password_hash(password)
        
        # IMPORTANT : On inclut email=email et bio=bio ici !
        new_user = User(
            username=username, 
            password=hashed_pw, 
            email=email, 
            phone=phone, 
            bio=bio if bio else "Salut, je suis sur VIBE AFRICA !"
        )
        
        try:
            db.session.add(new_user)
            db.session.commit()
            flash("Compte créé avec succès ! Connectez-vous.", "success")
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            print(f"Erreur d'insertion : {e}")
            flash("Une erreur interne est survenue.", "error")
            return redirect(url_for('register'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id 
            session['username'] = user.username
            return redirect(url_for('dashboard'))
        else:
            flash("Identifiants incorrects. Veuillez réessayer.", "error")
            return redirect(url_for('login'))
            
    return render_template('login.html')

@app.errorhandler(429)
def ratelimit_handler(e):
    return render_template('429.html'), 429

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()
        if user:
            token = s.dumps(user.id, salt='password-reset')
            msg = Message("Réinitialisation du mot de passe",
                          sender=app.config['MAIL_USERNAME'],
                          recipients=[user.email])
            msg.body = f"Bonjour {user.username},\n\nCliquez sur le lien suivant pour réinitialiser votre mot de passe :\n{url_for('reset_password', token=token, _external=True)}"
            mail.send(msg)
            flash("Un email de réinitialisation vous a été envoyé.", "success")
        else:
            flash("Aucun utilisateur trouvé avec cette adresse email.", "error")
    return render_template('forgot_password.html')

@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    try:
        user_id = s.loads(token, salt='password-reset', max_age=1800)
    except:
        flash("Le lien de réinitialisation est invalide ou a expiré.", "error")
        return redirect(url_for('login'))

    if request.method == 'POST':
        new_password = request.form.get('password')
        user = User.query.get(user_id)
        if user:
            user.password = generate_password_hash(new_password)
            db.session.commit()
            flash("Votre mot de passe a été mis à jour !", "success")
            return redirect(url_for('login'))
            
    return render_template('reset_password_form.html')

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

@app.route('/explorer')
def explorer():
    # Page principale avec les grands groupes (Boutique, École, etc.)
    return render_template('explorer.html')

@app.route('/explorer/<category>')
def explorer_category(category):
    # Dictionnaire des sous-activités
    sub_categories = {
        'divertissement': [
            {'name': 'Vidéos', 'icon': '🎬', 'link': '#'},
            {'name': 'Séries', 'icon': '📺', 'link': '#'},
            {'name': 'Musique', 'icon': '🎵', 'link': '#'}
        ],
        'boutique': [
            {'name': 'Vêtements', 'icon': '👕', 'link': '#'},
            {'name': 'Électronique', 'icon': '📱', 'link': '#'}
        ],
        'ecole': [
            {'name': 'Formations IT', 'icon': '💻', 'link': '#'},
            {'name': 'Cours Vidéo', 'icon': '📚', 'link': '#'}
        ]
    }
    
    data = sub_categories.get(category.lower(), [])
    return render_template('explorer_detail.html', category=category, items=data)

@app.route('/profile/')
@app.route('/profile/<username>')
def profile(username=None):
    # 1. Gestion des accès (Visiteur vs Connecté)
    if username is None and 'user_id' not in session:
        return render_template('profile_guest.html')

    if username is None and 'user_id' in session:
        username = session['username']
    
    # 2. Récupération de l'utilisateur ciblé
    user = User.query.filter_by(username=username).first_or_404()
    
    # 3. Récupération des données pour les onglets (Vibes, Likes, Favoris)
    # Mes publications
    vibes = Video.query.filter_by(user_id=user.id).order_by(Video.created_at.desc()).all()
    
    # Vidéos que j'ai likées (On cherche dans la table Like)
    liked_ids = [l.video_id for l in Like.query.filter_by(user_id=user.id).all()]
    liked_videos = Video.query.filter(Video.id.in_(liked_ids)).all() if liked_ids else []
    
    # Vidéos en favoris (On cherche dans la table Favorite)
    fav_ids = [f.video_id for f in Favorite.query.filter_by(user_id=user.id).all()]
    fav_videos = Video.query.filter(Video.id.in_(fav_ids)).all() if fav_ids else []
    
    # 4. Statistiques et Relations
    friends_count = FriendRequest.query.filter(
        ((FriendRequest.sender_id == user.id) | (FriendRequest.receiver_id == user.id)),
        (FriendRequest.status == 'accepted')
    ).count()
    
    me = None
    friendship = None
    is_own_profile = False
    
    if 'user_id' in session:
        me = User.query.get(session['user_id'])
        if me.id == user.id:
            is_own_profile = True
        
        # Vérification si nous sommes déjà amis
        friendship = FriendRequest.query.filter(
            ((FriendRequest.sender_id == me.id) & (FriendRequest.receiver_id == user.id)) |
            ((FriendRequest.sender_id == user.id) & (FriendRequest.receiver_id == me.id)),
            (FriendRequest.status == 'accepted')
        ).first()
        
    return render_template('profile.html', 
                           user=user, 
                           current_user_obj=me, 
                           friendship=friendship, 
                           vibes=vibes, 
                           liked_videos=liked_videos, # Nouveau
                           fav_videos=fav_videos,     # Nouveau
                           is_own_profile=is_own_profile,
                           friends_count=friends_count)

@app.route('/edit_profile', methods=['GET', 'POST'])
def edit_profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])
    
    if request.method == 'POST':
        user.username = request.form.get('username')
        user.bio = request.form.get('bio')
        user.phone = request.form.get('phone')
        
        file = request.files.get('profile_pic')
        if file and allowed_file(file.filename):
            filename = secure_filename(f"profile_{user.id}_{file.filename}")
            file.save(os.path.join(UPLOAD_FOLDER_PROFILES, filename))
            user.profile_pic = filename
            
        db.session.commit()
        flash("Ton profil a été mis à jour, @{} !".format(user.username))
        return redirect(url_for('profile', username=user.username))
        
    return render_template('edit_profile.html', user=user)

# --- ROUTE : LISTE DES AMIS ---
@app.route('/profile/<username>/friends')
def friends_list(username):
    user = User.query.filter_by(username=username).first_or_404()
    # On cherche tous les amis acceptés
    requests = FriendRequest.query.filter(
        ((FriendRequest.sender_id == user.id) | (FriendRequest.receiver_id == user.id)),
        (FriendRequest.status == 'accepted')
    ).all()
    
    friends = []
    for req in requests:
        friend_id = req.receiver_id if req.sender_id == user.id else req.sender_id
        friends.append(User.query.get(friend_id))
        
    return render_template('users_list.html', title="Amis de " + username, users=friends)

# --- ROUTE : LISTE DES ABONNÉS ---
@app.route('/profile/<username>/followers')
def followers_list(username):
    user = User.query.filter_by(username=username).first_or_404()
    return render_template('users_list.html', title="Abonnés de " + username, users=user.followers.all())

# --- ROUTE : FAVORIS (Toggle) ---
@app.route('/toggle_favorite/<int:video_id>', methods=['POST'])
def toggle_favorite(video_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    existing = Favorite.query.filter_by(user_id=user_id, video_id=video_id).first()
    
    if existing:
        db.session.delete(existing)
        flash("Retiré des favoris")
    else:
        new_fav = Favorite(user_id=user_id, video_id=video_id)
        db.session.add(new_fav)
        flash("Ajouté aux favoris ⭐")
        
    db.session.commit()
    return redirect(request.referrer or url_for('dashboard'))


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
        
        if file and file.filename != '':
            try:
                upload_result = cloudinary.uploader.upload(
                    file, 
                    resource_type="auto",
                    folder="vibe_africa_uploads"
                )
                file_url = upload_result['secure_url']
                
                new_video = Video(
                    title=title, 
                    filename=file_url,
                    user_id=session['user_id'], 
                    category=category
                )
                
                db.session.add(new_video)
                db.session.commit()
                return redirect(url_for('dashboard'))

            except Exception as e:
                print(f"Erreur lors de l'upload Cloudinary : {e}")
                return f"Erreur de mise en ligne : {e}", 500
            
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

@app.route('/vibe/<int:vibe_id>')
def view_vibe(vibe_id):
    vibe = Video.query.get_or_404(vibe_id)
    
    if vibe.views is None: vibe.views = 0
    vibe.views += 1
    db.session.commit()
    
    all_vibes = Video.query.order_by(Video.created_at.desc()).all()
    vibe_ids = [v.id for v in all_vibes]
    current_index = vibe_ids.index(vibe.id)
    
    next_id = vibe_ids[current_index + 1] if current_index + 1 < len(vibe_ids) else None
    prev_id = vibe_ids[current_index - 1] if current_index > 0 else None

    return render_template('view_vibe.html', 
                            vibe=vibe, 
                            next_id=next_id, 
                            prev_id=prev_id)

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
            new_msg = MessageModel(sender_id=me_id, receiver_id=friend_id, content=content)
            db.session.add(new_msg)
            db.session.commit()
            return redirect(url_for('chat', friend_id=friend_id))

    messages = MessageModel.query.filter(
        ((MessageModel.sender_id == me_id) & (MessageModel.receiver_id == friend_id)) |
        ((MessageModel.sender_id == friend_id) & (MessageModel.receiver_id == me_id))
    ).order_by(MessageModel.timestamp.asc()).all()
    
    return render_template('chat.html', messages=messages, friend=friend)

@app.route('/messages')
def messages_list():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    me_id = session['user_id']
    me = User.query.get(me_id)
    
    friends_relations = FriendRequest.query.filter(
        ((FriendRequest.sender_id == me_id) | (FriendRequest.receiver_id == me_id)),
        FriendRequest.status == 'accepted'
    ).all()
    
    friends = []
    for rel in friends_relations:
        f_id = rel.receiver_id if rel.sender_id == me_id else rel.sender_id
        friends.append(User.query.get(f_id))
        
    my_groups = me.groups.all()
    return render_template('messages_list.html', friends=friends, groups=my_groups)

@app.route('/create_group', methods=['POST'])
def create_group():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    group_name = request.form.get('name')
    if group_name:
        me = User.query.get(session['user_id'])
        new_group = Group(name=group_name, creator_id=me.id)
        new_group.members.append(me)
        db.session.add(new_group)
        db.session.commit()
        flash("Communauté créée avec succès !", "success")
        
    return redirect(url_for('messages_list'))

@app.route('/updates')
def show_updates():
    updates = AppUpdate.query.order_by(AppUpdate.date.desc()).all()
    return render_template('updates.html', updates=updates)

@app.route('/explorer/create', methods=['GET', 'POST'])
def create_business():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        name = request.form.get('name')
        category = request.form.get('category')
        description = request.form.get('description')
        
        new_biz = Business(
            name=name, 
            category=category, 
            description=description, 
            owner_id=session['user_id']
        )
        db.session.add(new_biz)
        db.session.commit()
        flash("Votre business a été créé avec succès !", "success")
        return redirect(url_for('explorer'))
        
    return render_template('create_business.html')

@app.route('/explorer/<category>')
def explorer_category(category):
    # On récupère tous les business créés par les utilisateurs pour cette catégorie
    businesses = Business.query.filter_by(category=category).all()
    return render_template('explorer_detail.html', category=category, businesses=businesses)

# --- ROUTES DE MAINTENANCE DE LA BASE ---


# --- INITIALISATION AU LANCEMENT ---

with app.app_context():
    # Crée les tables si elles n'existent pas
    db.create_all()
    print("VIBE AFRICA : Base de données prête et sécurisée.")

if __name__ == '__main__':
    app.run(debug=True)