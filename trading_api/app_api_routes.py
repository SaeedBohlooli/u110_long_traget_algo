from flask import Blueprint, request, jsonify
import logging
import os
import yaml
logger = logging.getLogger(__name__)

from pprint import pprint
app_bp = Blueprint("app_bp", __name__)


@app_bp.route("/api/get-closed-order-sets", methods=["GET"])
def get_order_history():
    pass

@app_bp.route("/api/save-file", methods=["POST"])
def save_file():
    pass