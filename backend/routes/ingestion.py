"""Machine-to-machine activity ingestion endpoint."""

import hmac
import logging
import os

from flask import Blueprint, jsonify, request

from backend.services.ingestion_service import (
    ingest_event,
    IngestionError,
    EventConflictError,
)
from backend.services.runtime_context_service import RuntimeContextError

ingestion_bp = Blueprint("ingestion", __name__)
logger = logging.getLogger(__name__)


@ingestion_bp.route("/ingest/events", methods=["POST"])
def receive_event():
    configured_key = os.getenv("ANOMEX_INGESTION_API_KEY")
    supplied_key = request.headers.get("X-API-Key", "")

    if not configured_key:
        return jsonify({
            "success": False,
            "message": "Ingestion endpoint is not configured.",
        }), 503

    if not supplied_key or not hmac.compare_digest(
        supplied_key, configured_key
    ):
        return jsonify({
            "success": False,
            "message": "Invalid or missing API key.",
        }), 401

    event = request.get_json(silent=True)
    if not isinstance(event, dict):
        return jsonify({
            "success": False,
            "message": "Request body must be a JSON object.",
        }), 400

    try:
        result = ingest_event(event)
        return jsonify({
            "success": True,
            "message": "Event processed.",
            **result,
        }), 200

    except EventConflictError as exc:
        return jsonify({
            "success": False,
            "message": str(exc),
        }), 409

    except (IngestionError, RuntimeContextError, ValueError) as exc:
        return jsonify({
            "success": False,
            "message": str(exc),
        }), 400

    except Exception:
        logger.exception("Runtime event ingestion failed.")
        return jsonify({
            "success": False,
            "message": "Event ingestion failed.",
        }), 500
