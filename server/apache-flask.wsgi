###############################################################################
#    WSGI Webアプリケーションのエントリーポイントです。
##############################################################################
import sys
sys.path.insert(0, "/var/www/apache-flask")
sys.path.insert(0, "/var/www/apache-flask/app")

from app.main import app as application
