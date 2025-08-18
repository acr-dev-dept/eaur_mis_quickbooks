from flask import Flask, current_app
from dotenv import load_dotenv
from flask_sqlalchemy import SQLAlchemy


load_dotenv()
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('SQLALCHEMY_DATABASE_URI')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['SECURITY_PASSWORD_SALT'] = secrets.token_urlsafe(32)
# Configure session to use filesystem (server-side session)
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

db = SQLAlchemy(app)
migrate = Migrate(app, db)
_ = jwt_config.jwt.init_app(app) # To avoid circular imports

# configure basic flask_jwt_extended configurations
app.config['JWT_SECRET_KEY'] = "this is secret key to be changed"
# app.config['JWT_ACCESS_TOKEN_EXPIRES'] = 30 * 60
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = 24 * 60 * 60 # for development
app.config['JWT_REFRESH_TOKEN_EXPIRES'] = 24 * 30 * 60 * 60 # To expire in a month
app.config['JWT_TOKEN_LOCATION'] = ['headers']

# Initialize the Database Connection Manager
app.config['db_connection'] = DatabaseConnection()
