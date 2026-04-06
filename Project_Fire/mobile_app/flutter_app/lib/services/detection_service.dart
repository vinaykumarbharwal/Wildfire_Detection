import 'dart:typed_data';
import 'package:flutter/foundation.dart';
import 'package:camera/camera.dart';
import 'package:image_picker/image_picker.dart';
import 'api_service.dart';

class DetectionService extends ChangeNotifier {
  bool _isModelLoaded = true; // Cloud model is always "loaded"
  bool _isProcessing = false;
  
  bool get isModelLoaded => _isModelLoaded;
  bool get isProcessing => _isProcessing;

  Future<bool> loadModel() async {
    // No-op for Cloud API
    return true;
  }

  Future<Map<String, dynamic>> detectFire(XFile imageFile, ApiService apiService, {double lat = 0.0, double lng = 0.0}) async {
    if (_isProcessing) return {'detected': false, 'error': 'Busy'};
    
    _isProcessing = true;
    notifyListeners();

    try {
      // Pass XFile directly — works on Web, Windows, Android, iOS
      final result = await apiService.detectFireCloud(imageFile, lat: lat, lng: lng);
      
      _isProcessing = false;
      notifyListeners();
      
      return result;
    } catch (e) {
      _isProcessing = false;
      notifyListeners();
      print('Detection error: $e');
      return {'detected': false, 'error': e.toString()};
    }
  }

  // Helper for web/mobile cross-platform
  Future<Map<String, dynamic>> detectFireBytes(Uint8List bytes, ApiService apiService) async {
     // Implementation for web if needed
     return {'detected': false};
  }
}
