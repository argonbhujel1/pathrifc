from flask import Blueprint

main_bp = Blueprint('main', __name__)
shop_bp = Blueprint('shop', __name__)
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

from . import main, shop, admin
