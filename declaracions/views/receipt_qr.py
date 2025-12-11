"""
QR Code Generation Endpoint

Generates encrypted QR code data for offline sync.
Includes complete nested data (declaracion + checkin + all foreign keys).
"""
import json
from datetime import datetime

from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from declaracions.models import Checkin
from declaracions.serializers import CheckinSerializer, DeclaracionSerializer
from declaracions.utils.qr_crypto import encrypt_qr_data


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def generate_offline_sync_qr(request, checkin_id):
    """
    Generate encrypted QR code data for offline sync.
    
    Returns complete nested data including:
    - Full Declaracion object with all foreign keys
    - Full Checkin object
    - Timestamp for expiry validation
    
    URL: /api/checkin/<checkin_id>/qr/
    """
    checkin = get_object_or_404(Checkin, id=checkin_id)
    
    # Only generate QR for completed/paid checkins
    if checkin.status not in ['success', 'paid']:
        return Response({
            'error': 'QR code can only be generated for completed checkins'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Serialize complete data
    checkin_data = CheckinSerializer(checkin).data
    declaracion_data = DeclaracionSerializer(checkin.declaracion).data if checkin.declaracion else None
    
    # Prepare QR payload
    qr_payload = {
        'version': '1.0',
        'type': 'offline_sync',
        'checkin_id': str(checkin.id),
        'declaracion': declaracion_data,
        'checkin': checkin_data,
        'timestamp': timezone.now().isoformat(),
        'source_station': str(checkin.station.id) if checkin.station else None,
    }
    
    # Convert to JSON
    json_payload = json.dumps(qr_payload, ensure_ascii=False)
    
    # Encrypt
    try:
        encrypted_data = encrypt_qr_data(json_payload)
    except Exception as e:
        return Response({
            'error': f'Encryption failed: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    return Response({
        'qr_data': encrypted_data,
        'checkin_id': str(checkin.id),
        'declaracion_number': checkin.declaracion.declaracio_number if checkin.declaracion else None,
        'generated_at': timezone.now().isoformat(),
    }, status=status.HTTP_200_OK)
