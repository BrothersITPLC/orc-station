"""
Offline Sync Endpoint

Receives and applies encrypted QR code data for offline synchronization.
Validates, decrypts, and upserts declaracion and checkin records.
"""
import json
from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from declaracions.models import Checkin, Declaracion
from declaracions.serializers import CheckinSerializer, DeclaracionSerializer
from declaracions.utils.qr_crypto import decrypt_qr_data


def upsert_declaracion_from_qr(declaracion_data: dict) -> Declaracion:
    """
    Create or update a Declaracion from QR data.
    Handles all nested foreign keys.
    """
    declaracion_id = declaracion_data.get('id')
    
    # Remove nested objects and use IDs
    simplified_data = {
        'id': declaracion_id,
        'declaracio_number': declaracion_data.get('declaracio_number'),
        'status': declaracion_data.get('status'),
        'register_by_id': declaracion_data.get('register_by', {}).get('id') if isinstance(declaracion_data.get('register_by'), dict) else declaracion_data.get('register_by'),
        'driver_id': declaracion_data.get('driver', {}).get('id') if isinstance(declaracion_data.get('driver'), dict) else declaracion_data.get('driver'),
        'truck_id': declaracion_data.get('truck', {}).get('id') if isinstance(declaracion_data.get('truck'), dict) else declaracion_data.get('truck'),
        'exporter_id': declaracion_data.get('exporter', {}).get('id') if isinstance(declaracion_data.get('exporter'), dict) else declaracion_data.get('exporter'),
        'path_id': declaracion_data.get('path', {}).get('id') if isinstance(declaracion_data.get('path'), dict) else declaracion_data.get('path'),
        'commodity_id': declaracion_data.get('commodity', {}).get('id') if isinstance(declaracion_data.get('commodity'), dict) else declaracion_data.get('commodity'),
    }
    
    # Filter out None values
    simplified_data = {k: v for k, v in simplified_data.items() if v is not None}
    
    declaracion, created = Declaracion.objects.update_or_create(
        id=declaracion_id,
        defaults=simplified_data
    )
    
    return declaracion


def upsert_checkin_from_qr(checkin_data: dict, declaracion: Declaracion) -> tuple[Checkin, bool]:
    """
    Create or update a Checkin from QR data.
    Sets the _offline_synced flag to True.
    """
    checkin_id = checkin_data.get('id')
    
    # Remove nested objects and use IDs
    simplified_data = {
        'id': checkin_id,
        'Tage': checkin_data.get('Tage'),
        'receipt_number': checkin_data.get('receipt_number'),
        'deduction': checkin_data.get('deduction', 0),
        'station_id': checkin_data.get('station', {}).get('id') if isinstance(checkin_data.get('station'), dict) else checkin_data.get('station'),
        'employee_id': checkin_data.get('employee', {}).get('id') if isinstance(checkin_data.get('employee'), dict) else checkin_data.get('employee'),
        'payment_accepter_id': checkin_data.get('payment_accepter', {}).get('id') if isinstance(checkin_data.get('payment_accepter'), dict) else checkin_data.get('payment_accepter'),
        'status': checkin_data.get('status'),
        'transaction_key': checkin_data.get('transaction_key'),
        'payment_method_id': checkin_data.get('payment_method', {}).get('id') if isinstance(checkin_data.get('payment_method'), dict) else checkin_data.get('payment_method'),
        'confirmation_code': checkin_data.get('confirmation_code'),
        'net_weight': checkin_data.get('net_weight'),
        'description': checkin_data.get('description'),
        'unit_price': checkin_data.get('unit_price'),
        'rate': checkin_data.get('rate'),
        'declaracion': declaracion,
        '_offline_synced': True,  # Mark as offline-synced
    }
    
    # Filter out None values except for boolean
    simplified_data = {k: v for k, v in simplified_data.items() if v is not None or k == '_offline_synced'}
    
    checkin, created = Checkin.objects.update_or_create(
        id=checkin_id,
        defaults=simplified_data
    )
    
    return checkin, created


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def offline_sync_checkin(request):
    """
    Receive and apply offline sync data from QR code scan.
    
    Expected payload:
    {
        "qr_data": "encrypted_base64_string"
    }
    
    URL: /api/offline-sync/
    """
    encrypted_data = request.data.get('qr_data')
    
    if not encrypted_data:
        return Response({
            'error': 'qr_data field is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Decrypt
    try:
        decrypted_json = decrypt_qr_data(encrypted_data)
        qr_payload = json.loads(decrypted_json)
    except ValueError as e:
        return Response({
            'error': f'Failed to decrypt QR data: {str(e)}'
        }, status=status.HTTP_400_BAD_REQUEST)
    except json.JSONDecodeError:
        return Response({
            'error': 'Invalid JSON in QR data'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Validate version
    if qr_payload.get('version') != '1.0':
        return Response({
            'error': 'Unsupported QR code version'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Validate type
    if qr_payload.get('type') != 'offline_sync':
        return Response({
            'error': 'Invalid QR code type'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Validate timestamp (24 hour expiry)
    qr_timestamp_str = qr_payload.get('timestamp')
    if not qr_timestamp_str:
        return Response({
            'error': 'QR code missing timestamp'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    qr_timestamp = parse_datetime(qr_timestamp_str)
    if not qr_timestamp:
        return Response({
            'error': 'Invalid timestamp format'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Make timezone-aware if naive
    if timezone.is_naive(qr_timestamp):
        qr_timestamp = timezone.make_aware(qr_timestamp)
    
    age = timezone.now() - qr_timestamp
    if age > timedelta(hours=24):
        return Response({
            'error': f'QR code expired (age: {age.total_seconds() / 3600:.1f} hours)'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Extract data
    declaracion_data = qr_payload.get('declaracion')
    checkin_data = qr_payload.get('checkin')
    
    if not declaracion_data or not checkin_data:
        return Response({
            'error': 'QR code missing declaracion or checkin data'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Apply data in transaction
    try:
        with transaction.atomic():
            # Upsert declaracion
            declaracion = upsert_declaracion_from_qr(declaracion_data)
            
            # Upsert checkin
            checkin, created = upsert_checkin_from_qr(checkin_data, declaracion)
            
        return Response({
            'status': 'success',
            'message': f"{'Created' if created else 'Updated'} checkin via offline sync",
            'checkin_id': str(checkin.id),
            'declaracion_number': declaracion.declaracio_number,
            'already_existed': not created,
            'offline_synced': True,
            'source_station': qr_payload.get('source_station'),
            'synced_by': request.user.username,
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'error': f'Failed to apply offline sync: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
