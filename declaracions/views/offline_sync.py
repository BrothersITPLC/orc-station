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
    
    # Handle "OFFLINE:" prefix if present
    if encrypted_data.startswith("OFFLINE:"):
        encrypted_data = encrypted_data[8:]
        
    # Handle URL encoding issues (space to +)
    encrypted_data = encrypted_data.replace(' ', '+')
    
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
    
    
    # Handle new minimal payload format (v1.0+)
    # New format has declaracion_id, checkin_id instead of full objects
    declaracion_id = qr_payload.get('declaracion_id')
    checkin_id = qr_payload.get('checkin_id')
    
    if not declaracion_id or not checkin_id:
        # Fallback: Check for old format (full objects)
        declaracion_data = qr_payload.get('declaracion')
        checkin_data = qr_payload.get('checkin')
        
        if not declaracion_data or not checkin_data:
            return Response({
                'error': 'QR code missing required data (need declaracion_id/checkin_id or declaracion/checkin)'
            }, status=status.HTTP_400_BAD_REQUEST)
    
    
    # Process legacy format with full objects
        try:
            with transaction.atomic():
                declaracion = upsert_declaracion_from_qr(declaracion_data)
                checkin, created = upsert_checkin_from_qr(checkin_data, declaracion)
                
            return Response({
                'status': 'success',
                'message': f"{'Created' if created else 'Updated'} checkin via offline sync (legacy)",
                'checkin_id': str(checkin.id),
                'declaracion_number': declaracion.declaracio_number,
                'already_existed': not created,
                'offline_synced': True,
                'source_station': qr_payload.get('source_station'),
                'synced_by': request.user.username,
            }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
        except Exception as e:
            return Response({
                'error': f'Failed to apply offline sync (legacy): {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    # Process new minimal format (IDs only)
    # QR contains all required foreign key IDs to create records at receiving station
    try:
        with transaction.atomic():
            # Create or get Declaracion with all required foreign keys
            declaracion_defaults = {
                'declaracio_number': qr_payload.get('declaracion_number', ''),
                'truck_id': qr_payload.get('truck_id'),
                'driver_id': qr_payload.get('driver_id'),
                'exporter_id': qr_payload.get('exporter_id'),
                'commodity_id': qr_payload.get('commodity_id'),
                'path_id': qr_payload.get('path_id'),
                'register_by_id': qr_payload.get('register_by_id'),
                'status': 'PENDING',  # Will be updated when synced fully
            }
          
            # Filter out None values
            declaracion_defaults = {k: v for k, v in declaracion_defaults.items() if v is not None}
            
            declaracion, decl_created = Declaracion.objects.get_or_create(
                id=declaracion_id,
                defaults=declaracion_defaults
            )
            
            # Create/update checkin with data from QR
            checkin_defaults = {
                'declaracion': declaracion,
                'status': qr_payload.get('status'),
                'net_weight': qr_payload.get('net_weight'),
                'rate': qr_payload.get('rate'),
                'unit_price': qr_payload.get('unit_price'),
                '_offline_synced': True,
            }
            
            source_station_id = qr_payload.get('source_station_id')
            if source_station_id:
                checkin_defaults['station_id'] = source_station_id
            
            # Filter out None values
            checkin_defaults = {k: v for k, v in checkin_defaults.items() if v is not None}
            
            checkin, created = Checkin.objects.update_or_create(
                id=checkin_id,
                defaults=checkin_defaults
            )
            
        return Response({
            'status': 'success',
            'message': f"{'Created' if created else 'Updated'} checkin via offline sync",
            'checkin_id': str(checkin.id),
            'declaracion_id': str(declaracion.id),
            'declaracion_number': declaracion.declaracio_number,
            'declaracion_created': decl_created,
            'checkin_created': created,
            'offline_synced': True,
            'truck_plate': qr_payload.get('truck_plate'),
            'synced_by': request.user.username,
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'error': f'Failed to apply offline sync: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
