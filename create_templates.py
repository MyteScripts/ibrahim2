import os

# Ensure templates directory exists
os.makedirs("templates", exist_ok=True)

# Base Template
base_html = '''<!DOCTYPE html>
<html lang="en" data-bs-theme="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Discord Message Tracker - {% block title %}{% endblock %}</title>
    <link rel="stylesheet" href="https://cdn.replit.com/agent/bootstrap-agent-dark-theme.min.css">
    <style>
        .message-count {
            font-size: 1.2rem;
            font-weight: bold;
        }
        .navbar-brand {
            font-weight: bold;
        }
        .member-card {
            transition: transform 0.2s;
        }
        .member-card:hover {
            transform: translateY(-5px);
        }
        .stats-box {
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 20px;
            background-color: rgba(0, 0, 0, 0.2);
        }
    </style>
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark mb-4">
        <div class="container">
            <a class="navbar-brand" href="{{ url_for('index') }}">
                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="currentColor" class="bi bi-chat-dots me-2" viewBox="0 0 16 16">
                    <path d="M5 8a1 1 0 1 1-2 0 1 1 0 0 1 2 0zm4 0a1 1 0 1 1-2 0 1 1 0 0 1 2 0zm3 1a1 1 0 1 0 0-2 1 1 0 0 0 0 2z"/>
                    <path d="m2.165 15.803.02-.004c1.83-.363 2.948-.842 3.468-1.105A9.06 9.06 0 0 0 8 15c4.418 0 8-3.134 8-7s-3.582-7-8-7-8 3.134-8 7c0 1.76.743 3.37 1.97 4.6a10.437 10.437 0 0 1-.524 2.318l-.003.011a10.722 10.722 0 0 1-.244.637c-.079.186.074.394.273.362a21.673 21.673 0 0 0 .693-.125zm.8-3.108a1 1 0 0 0-.287-.801C1.618 10.83 1 9.468 1 8c0-3.192 3.004-6 7-6s7 2.808 7 6c0 3.193-3.004 6-7 6a8.06 8.06 0 0 1-2.088-.272 1 1 0 0 0-.711.074c-.387.196-1.24.57-2.634.893a10.97 10.97 0 0 0 .398-2z"/>
                </svg>
                Discord Message Tracker
            </a>
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav" aria-controls="navbarNav" aria-expanded="false" aria-label="Toggle navigation">
                <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse" id="navbarNav">
                <ul class="navbar-nav ms-auto">
                    <li class="nav-item">
                        <a class="nav-link" href="{{ url_for('index') }}">Home</a>
                    </li>
                    {% if current_user.is_authenticated %}
                    <li class="nav-item">
                        <a class="nav-link" href="{{ url_for('dashboard') }}">Dashboard</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="{{ url_for('add_server') }}">Add Server</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="{{ url_for('logout') }}">Logout</a>
                    </li>
                    {% else %}
                    <li class="nav-item">
                        <a class="nav-link" href="{{ url_for('login') }}">Login</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="{{ url_for('register') }}">Register</a>
                    </li>
                    {% endif %}
                </ul>
            </div>
        </div>
    </nav>

    <div class="container">
        {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}
            {% for category, message in messages %}
                <div class="alert alert-{{ category }} alert-dismissible fade show" role="alert">
                    {{ message }}
                    <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                </div>
            {% endfor %}
        {% endif %}
        {% endwith %}

        {% block content %}{% endblock %}
    </div>

    <footer class="mt-5 py-3 text-center text-muted">
        <div class="container">
            <p>&copy; 2025 Discord Message Tracker</p>
        </div>
    </footer>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    {% block scripts %}{% endblock %}
</body>
</html>'''

# Index Template
index_html = '''{% extends "base.html" %}
{% block title %}Home{% endblock %}

{% block content %}
<div class="container">
    <div class="row justify-content-center">
        <div class="col-md-8 text-center">
            <h1 class="display-4 mb-4">Track Discord Messages</h1>
            <p class="lead mb-5">Easily track and analyze the activity of your Discord server members.</p>
            
            <div class="row">
                <div class="col-md-4">
                    <div class="card mb-4 h-100">
                        <div class="card-body text-center">
                            <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" fill="currentColor" class="bi bi-bar-chart-fill mb-3 text-primary" viewBox="0 0 16 16">
                                <path d="M1 11a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v3a1 1 0 0 1-1 1H2a1 1 0 0 1-1-1v-3zm5-4a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v7a1 1 0 0 1-1 1H7a1 1 0 0 1-1-1V7zm5-5a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v12a1 1 0 0 1-1 1h-2a1 1 0 0 1-1-1V2z"/>
                            </svg>
                            <h3>Activity Tracking</h3>
                            <p>Monitor member activity with message counts and timestamps.</p>
                        </div>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="card mb-4 h-100">
                        <div class="card-body text-center">
                            <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" fill="currentColor" class="bi bi-trophy-fill mb-3 text-warning" viewBox="0 0 16 16">
                                <path d="M2.5.5A.5.5 0 0 1 3 0h10a.5.5 0 0 1 .5.5c0 .538-.012 1.05-.034 1.536a3 3 0 1 1-1.133 5.89c-.79 1.865-1.878 2.777-2.833 3.011v2.173l1.425.356c.194.048.377.135.537.255L13.3 15.1a.5.5 0 0 1-.3.9H3a.5.5 0 0 1-.3-.9l1.838-1.379c.16-.12.343-.207.537-.255L6.5 13.11v-2.173c-.955-.234-2.043-1.146-2.833-3.012a3 3 0 1 1-1.132-5.89A33.076 33.076 0 0 1 2.5.5zm.099 2.54a2 2 0 0 0 .72 3.935c-.333-1.05-.588-2.346-.72-3.935zm10.083 3.935a2 2 0 0 0 .72-3.935c-.133 1.59-.388 2.885-.72 3.935z"/>
                            </svg>
                            <h3>Leaderboards</h3>
                            <p>See who's most active in your server with real-time leaderboards.</p>
                        </div>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="card mb-4 h-100">
                        <div class="card-body text-center">
                            <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" fill="currentColor" class="bi bi-robot mb-3 text-info" viewBox="0 0 16 16">
                                <path d="M6 12.5a.5.5 0 0 1 .5-.5h3a.5.5 0 0 1 0 1h-3a.5.5 0 0 1-.5-.5ZM3 8.062C3 6.76 4.235 5.765 5.53 5.886a26.58 26.58 0 0 0 4.94 0C11.765 5.765 13 6.76 13 8.062v1.157a.933.933 0 0 1-.765.935c-.845.147-2.34.346-4.235.346-1.895 0-3.39-.2-4.235-.346A.933.933 0 0 1 3 9.219V8.062Zm4.542-.827a.25.25 0 0 0-.217.068l-.92.9a24.767 24.767 0 0 1-1.871-.183.25.25 0 0 0-.068.495c.55.076 1.232.149 2.02.193a.25.25 0 0 0 .189-.071l.754-.736.847 1.71a.25.25 0 0 0 .404.062l.932-.97a25.286 25.286 0 0 0 1.922-.188.25.25 0 0 0-.068-.495c-.538.074-1.207.145-1.98.189a.25.25 0 0 0-.166.076l-.754.785-.842-1.7a.25.25 0 0 0-.182-.135Z"/>
                                <path d="M8.5 1.866a1 1 0 1 0-1 0V3h-2A4.5 4.5 0 0 0 1 7.5V8a1 1 0 0 0-1 1v2a1 1 0 0 0 1 1v1a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-1a1 1 0 0 0 1-1V9a1 1 0 0 0-1-1v-.5A4.5 4.5 0 0 0 10.5 3h-2V1.866ZM14 7.5V13a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V7.5A3.5 3.5 0 0 1 5.5 4h5A3.5 3.5 0 0 1 14 7.5Z"/>
                            </svg>
                            <h3>Discord Bot Integration</h3>
                            <p>Automatically collect data with our powerful Discord bot.</p>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="mt-5">
                {% if current_user.is_authenticated %}
                    <a href="{{ url_for('dashboard') }}" class="btn btn-primary btn-lg">Go to Dashboard</a>
                {% else %}
                    <a href="{{ url_for('register') }}" class="btn btn-primary btn-lg me-2">Get Started</a>
                    <a href="{{ url_for('login') }}" class="btn btn-outline-secondary btn-lg">Login</a>
                {% endif %}
            </div>
        </div>
    </div>
</div>
{% endblock %}'''

# Login Template
login_html = '''{% extends "base.html" %}
{% block title %}Login{% endblock %}

{% block content %}
<div class="row justify-content-center">
    <div class="col-md-6">
        <div class="card">
            <div class="card-header">
                <h2 class="card-title">Login</h2>
            </div>
            <div class="card-body">
                <form method="POST" action="{{ url_for('login') }}">
                    <div class="mb-3">
                        <label for="username" class="form-label">Username</label>
                        <input type="text" class="form-control" id="username" name="username" required>
                    </div>
                    <div class="mb-3">
                        <label for="password" class="form-label">Password</label>
                        <input type="password" class="form-control" id="password" name="password" required>
                    </div>
                    <button type="submit" class="btn btn-primary">Login</button>
                </form>
                <div class="mt-3">
                    <p>Don't have an account? <a href="{{ url_for('register') }}">Register here</a></p>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}'''

# Register Template
register_html = '''{% extends "base.html" %}
{% block title %}Register{% endblock %}

{% block content %}
<div class="row justify-content-center">
    <div class="col-md-6">
        <div class="card">
            <div class="card-header">
                <h2 class="card-title">Create Account</h2>
            </div>
            <div class="card-body">
                <form method="POST" action="{{ url_for('register') }}">
                    <div class="mb-3">
                        <label for="username" class="form-label">Username</label>
                        <input type="text" class="form-control" id="username" name="username" required>
                    </div>
                    <div class="mb-3">
                        <label for="password" class="form-label">Password</label>
                        <input type="password" class="form-control" id="password" name="password" required>
                    </div>
                    <button type="submit" class="btn btn-primary">Create Account</button>
                </form>
                <div class="mt-3">
                    <p>Already have an account? <a href="{{ url_for('login') }}">Login here</a></p>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}'''

# Dashboard Template
dashboard_html = '''{% extends "base.html" %}
{% block title %}Dashboard{% endblock %}

{% block content %}
<div class="row">
    <div class="col-md-12 mb-4">
        <h1>Your Discord Servers</h1>
        <p class="lead">View and manage your connected Discord servers.</p>
    </div>
</div>

<div class="mb-4">
    <a href="{{ url_for('add_server') }}" class="btn btn-primary">
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-plus-circle me-2" viewBox="0 0 16 16">
            <path d="M8 15A7 7 0 1 1 8 1a7 7 0 0 1 0 14zm0 1A8 8 0 1 0 8 0a8 8 0 0 0 0 16z"/>
            <path d="M8 4a.5.5 0 0 1 .5.5v3h3a.5.5 0 0 1 0 1h-3v3a.5.5 0 0 1-1 0v-3h-3a.5.5 0 0 1 0-1h3v-3A.5.5 0 0 1 8 4z"/>
        </svg>
        Add Server
    </a>
</div>

{% if servers %}
    <div class="row">
        {% for server in servers %}
        <div class="col-md-4 mb-4">
            <div class="card h-100">
                <div class="card-body">
                    <h5 class="card-title">{{ server.name }}</h5>
                    <p class="card-text">Server ID: {{ server.id }}</p>
                </div>
                <div class="card-footer bg-transparent border-top-0">
                    <a href="{{ url_for('server_detail', server_id=server.id) }}" class="btn btn-primary">View Details</a>
                </div>
            </div>
        </div>
        {% endfor %}
    </div>
{% else %}
    <div class="alert alert-info">
        <p>You don't have any Discord servers added yet. Click the "Add Server" button to get started.</p>
    </div>
{% endif %}
{% endblock %}'''

# Server Detail Template
server_detail_html = '''{% extends "base.html" %}
{% block title %}{{ server.name }}{% endblock %}

{% block content %}
<div class="row mb-4">
    <div class="col-md-12">
        <h1>{{ server.name }}</h1>
        <p class="text-muted">Server ID: {{ server.id }}</p>
    </div>
</div>

<div class="row mb-4">
    <div class="col-md-4">
        <div class="stats-box">
            <h4>Total Messages</h4>
            <p class="display-4">{{ members|sum(attribute='message_count') }}</p>
        </div>
    </div>
    <div class="col-md-4">
        <div class="stats-box">
            <h4>Active Members</h4>
            <p class="display-4">{{ members|length }}</p>
        </div>
    </div>
    <div class="col-md-4">
        <div class="stats-box">
            <h4>Average Messages</h4>
            <p class="display-4">
                {% if members|length > 0 %}
                    {{ (members|sum(attribute='message_count') / members|length)|int }}
                {% else %}
                    0
                {% endif %}
            </p>
        </div>
    </div>
</div>

<div class="row mb-4">
    <div class="col-md-12">
        <div class="card">
            <div class="card-header">
                <h2>Member Leaderboard</h2>
            </div>
            <div class="card-body">
                <div class="table-responsive">
                    <table class="table table-hover">
                        <thead>
                            <tr>
                                <th>Rank</th>
                                <th>Username</th>
                                <th>Messages</th>
                                <th>Last Active</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for member in members %}
                            <tr>
                                <td>{{ loop.index }}</td>
                                <td>{{ member.username }}</td>
                                <td class="message-count">{{ member.message_count }}</td>
                                <td>{{ member.last_active.strftime('%Y-%m-%d %H:%M') if member.last_active else 'N/A' }}</td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>
</div>

<div class="row mb-4">
    <div class="col-md-12">
        <div class="card">
            <div class="card-header">
                <h2>Bot Integration</h2>
            </div>
            <div class="card-body">
                <h5>Add the Discord bot to your server</h5>
                <p>To track messages, you need to add our Discord bot to your server and set up the following:</p>
                
                <div class="mb-3">
                    <h6>1. Add the bot to your server</h6>
                    <a href="#" class="btn btn-primary">Add Bot to Server</a>
                </div>
                
                <div class="mb-3">
                    <h6>2. Configure your Discord bot with these settings:</h6>
                    <div class="bg-dark p-3 rounded">
                        <code>
                            SERVER_ID={{ server.id }}<br>
                            API_ENDPOINT={{ request.host_url }}api/update_message_count<br>
                            API_KEY=your_api_key_here
                        </code>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}'''

# Add Server Template
add_server_html = '''{% extends "base.html" %}
{% block title %}Add Server{% endblock %}

{% block content %}
<div class="row justify-content-center">
    <div class="col-md-6">
        <div class="card">
            <div class="card-header">
                <h2 class="card-title">Add Discord Server</h2>
            </div>
            <div class="card-body">
                <form method="POST" action="{{ url_for('add_server') }}">
                    <div class="mb-3">
                        <label for="server_id" class="form-label">Server ID</label>
                        <input type="text" class="form-control" id="server_id" name="server_id" required>
                        <div class="form-text">The Discord server ID (right-click on the server and select "Copy ID")</div>
                    </div>
                    <div class="mb-3">
                        <label for="server_name" class="form-label">Server Name</label>
                        <input type="text" class="form-control" id="server_name" name="server_name" required>
                    </div>
                    <button type="submit" class="btn btn-primary">Add Server</button>
                </form>
            </div>
        </div>
        
        <div class="card mt-4">
            <div class="card-header">
                <h2 class="card-title">How to find your Server ID</h2>
            </div>
            <div class="card-body">
                <ol>
                    <li>Open Discord</li>
                    <li>Go to User Settings > Advanced and enable "Developer Mode"</li>
                    <li>Right-click on your server icon</li>
                    <li>Select "Copy ID" from the menu</li>
                </ol>
            </div>
        </div>
    </div>
</div>
{% endblock %}'''

# Write templates to files
with open("templates/base.html", "w") as f:
    f.write(base_html)

with open("templates/index.html", "w") as f:
    f.write(index_html)

with open("templates/login.html", "w") as f:
    f.write(login_html)

with open("templates/register.html", "w") as f:
    f.write(register_html)

with open("templates/dashboard.html", "w") as f:
    f.write(dashboard_html)

with open("templates/server_detail.html", "w") as f:
    f.write(server_detail_html)

with open("templates/add_server.html", "w") as f:
    f.write(add_server_html)

print("Template files have been created successfully!")