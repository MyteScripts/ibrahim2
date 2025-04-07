import os
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

# Create the Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "a-default-secret-key")

# Configure the database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize SQLAlchemy
db = SQLAlchemy(app)

# Initialize LoginManager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


# Database Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)


class DiscordServer(db.Model):
    id = db.Column(db.String(20), primary_key=True)  # Discord server ID
    name = db.Column(db.String(100), nullable=False)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Relationship
    members = db.relationship('ServerMember', backref='server', lazy=True)


class ServerMember(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    discord_id = db.Column(db.String(20), nullable=False)
    server_id = db.Column(db.String(20), db.ForeignKey('discord_server.id'), nullable=False)
    username = db.Column(db.String(100), nullable=False)
    message_count = db.Column(db.Integer, default=0)
    last_active = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Composite unique constraint
    __table_args__ = (db.UniqueConstraint('discord_id', 'server_id', name='unique_member_server'),)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# Create tables if they don't exist
with app.app_context():
    db.create_all()


# Routes
@app.route('/')
def index():
    """Home page"""
    return render_template('index.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    """Register a new user account"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Check if username already exists
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists', 'danger')
            return redirect(url_for('register'))
        
        # Create new user
        new_user = User(
            username=username,
            password_hash=generate_password_hash(password)
        )
        
        # First user is admin
        if User.query.count() == 0:
            new_user.is_admin = True
        
        db.session.add(new_user)
        db.session.commit()
        
        flash('Account created successfully! You can now log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard'))
        else:
            flash('Login failed. Please check your username and password.', 'danger')
    
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    """Logout the current user"""
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('index'))


@app.route('/dashboard')
@login_required
def dashboard():
    """Main dashboard showing servers"""
    servers = DiscordServer.query.filter_by(owner_id=current_user.id).all()
    return render_template('dashboard.html', servers=servers)


@app.route('/server/<server_id>')
@login_required
def server_detail(server_id):
    """Detail view for a specific server"""
    server = DiscordServer.query.get_or_404(server_id)
    
    # Check if the current user owns this server
    if server.owner_id != current_user.id and not current_user.is_admin:
        flash('You do not have permission to view this server', 'danger')
        return redirect(url_for('dashboard'))
    
    # Get all members of this server
    members = ServerMember.query.filter_by(server_id=server_id).order_by(ServerMember.message_count.desc()).all()
    
    return render_template('server_detail.html', server=server, members=members)


@app.route('/add_server', methods=['GET', 'POST'])
@login_required
def add_server():
    """Add a new Discord server to track"""
    if request.method == 'POST':
        server_id = request.form.get('server_id')
        server_name = request.form.get('server_name')
        
        # Check if server already exists
        existing_server = DiscordServer.query.get(server_id)
        if existing_server:
            flash('Server with this ID already exists', 'danger')
            return redirect(url_for('add_server'))
        
        # Create new server
        new_server = DiscordServer(
            id=server_id,
            name=server_name,
            owner_id=current_user.id
        )
        
        db.session.add(new_server)
        db.session.commit()
        
        flash('Server added successfully!', 'success')
        return redirect(url_for('dashboard'))
    
    return render_template('add_server.html')


# API Endpoints for the Discord bot
@app.route('/api/update_message_count', methods=['POST'])
def update_message_count():
    """API endpoint for the Discord bot to update message counts"""
    # Simple API key auth (should be improved in production)
    api_key = request.headers.get('API-Key')
    if not api_key or api_key != os.environ.get('MESSAGE_TRACKER_API_KEY', 'default-api-key'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.json
    required_fields = ['server_id', 'server_name', 'discord_id', 'username']
    
    # Validate required fields
    if not all(field in data for field in required_fields):
        return jsonify({'error': 'Missing required fields'}), 400
    
    server_id = data['server_id']
    server_name = data['server_name']
    discord_id = data['discord_id']
    username = data['username']
    
    # Find or create server
    server = DiscordServer.query.get(server_id)
    if not server:
        # Find any admin user to set as owner
        admin = User.query.filter_by(is_admin=True).first()
        if not admin:
            # If no admin, get the first user
            admin = User.query.first()
        
        if not admin:
            return jsonify({'error': 'No users exist in the system'}), 500
        
        server = DiscordServer(
            id=server_id,
            name=server_name,
            owner_id=admin.id
        )
        db.session.add(server)
    
    # Find or create member
    member = ServerMember.query.filter_by(discord_id=discord_id, server_id=server_id).first()
    if not member:
        member = ServerMember(
            discord_id=discord_id,
            server_id=server_id,
            username=username,
            message_count=0
        )
        db.session.add(member)
    
    # Update member info
    member.username = username  # In case they changed their username
    member.message_count += 1
    member.last_active = datetime.utcnow()
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'member': {
            'discord_id': member.discord_id,
            'username': member.username,
            'message_count': member.message_count
        }
    })


@app.route('/api/server_stats/<server_id>')
def server_stats(server_id):
    """Public API endpoint to get server stats"""
    server = DiscordServer.query.get_or_404(server_id)
    members = ServerMember.query.filter_by(server_id=server_id).order_by(ServerMember.message_count.desc()).all()
    
    stats = {
        'server_id': server.id,
        'server_name': server.name,
        'total_messages': sum(member.message_count for member in members),
        'member_count': len(members),
        'members': [
            {
                'discord_id': member.discord_id,
                'username': member.username,
                'message_count': member.message_count,
                'last_active': member.last_active.isoformat() if member.last_active else None
            }
            for member in members
        ]
    }
    
    return jsonify(stats)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)