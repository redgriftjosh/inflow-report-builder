# Database setup
username = "jredgrift"        # you may put your username instead
password = "PythonDatabase@1"  # use your MySQL password
hostname = f"{username}.mysql.pythonanywhere-services.com"
databasename = f"{username}$asyncinweb"

SQLALCHEMY_DATABASE_URI = (
    f"mysql://{username}:{password}@{hostname}/{databasename}"
)

SQLALCHEMY_ENGINE_OPTIONS = {"pool_recycle": 299}
SQLALCHEMY_TRACK_MODIFICATIONS = False