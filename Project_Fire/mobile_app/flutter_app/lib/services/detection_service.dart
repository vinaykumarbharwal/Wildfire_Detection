import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:camera/camera.dart';
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

  Future<Map<String, dynamic>> detectFire(XFile imageFile, ApiService apiService) async {
    if (_isProcessing) return {'detected': false, 'error': 'Busy'};
    
    _isProcessing = true;
    notifyListeners();

    try {
      final File file = File(imageFile.path);
      final result = await apiService.detectFireCloud(file);
      
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
