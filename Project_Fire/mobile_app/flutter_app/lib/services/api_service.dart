import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;
import 'package:flutter/material.dart';
import 'package:location/location.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../utils/constants.dart';

class ApiService extends ChangeNotifier {
  static const String baseUrl = AppConstants.baseUrl;
  String? _authToken;
  
  Future<Map<String, dynamic>> reportDetection({
    required Map<String, dynamic> detection,
    required File imageFile,
  }) async {
    try {
      // Get location
      Location location = Location();
      bool serviceEnabled = await location.serviceEnabled();
      if (!serviceEnabled) {
        serviceEnabled = await location.requestService();
        if (!serviceEnabled) {
          throw Exception('Location services are disabled');
        }
      }
      
      PermissionStatus permissionGranted = await location.hasPermission();
      if (permissionGranted == PermissionStatus.denied) {
        permissionGranted = await location.requestPermission();
        if (permissionGranted != PermissionStatus.granted) {
          throw Exception('Location permissions are denied');
        }
      }
      
      var currentLocation = await location.getLocation();
      
      // Create multipart request
      var uri = Uri.parse('$baseUrl/detections/report');
      var request = http.MultipartRequest('POST', uri);
      
      // Add image file
      request.files.add(
        await http.MultipartFile.fromPath(
          'image',
          imageFile.path,
          filename: 'detection_${DateTime.now().millisecondsSinceEpoch}.jpg',
        ),
      );
      
      // Add fields
      request.fields['latitude'] = currentLocation.latitude.toString();
      request.fields['longitude'] = currentLocation.longitude.toString();
      request.fields['confidence'] = detection['confidence'].toString();
      request.fields['timestamp'] = detection['timestamp'];
      
      // Add auth token if available
      if (_authToken != null) {
        request.headers['Authorization'] = 'Bearer $_authToken';
      }
      
      // Send request
      var streamedResponse = await request.send();
      var response = await http.Response.fromStream(streamedResponse);
      
      if (response.statusCode == 200) {
        var data = json.decode(response.body);
        print('✅ Detection reported: ${data['detection_id']}');
        return data;
      } else {
        throw Exception('Server error: ${response.statusCode}');
      }
      
    } catch (e) {
      print('❌ Error reporting detection: $e');
      throw Exception('Failed to report detection: $e');
    }
  }

  Future<List<dynamic>> getDetections({int limit = 50}) async {
    try {
      var uri = Uri.parse('$baseUrl/detections?limit=$limit');
      var response = await http.get(uri);
      
      if (response.statusCode == 200) {
        return json.decode(response.body);
      } else {
        throw Exception('Failed to load detections');
      }
    } catch (e) {
      print('Error loading detections: $e');
      return [];
    }
  }

  Future<Map<String, dynamic>> getStats() async {
    try {
      var uri = Uri.parse('$baseUrl/stats');
      var response = await http.get(uri);
      
      if (response.statusCode == 200) {
        return json.decode(response.body);
      } else {
        throw Exception('Failed to load stats');
      }
    } catch (e) {
      print('Error loading stats: $e');
      return {};
    }
  }

  Future<bool> login(String email, String password) async {
    try {
      var uri = Uri.parse('$baseUrl/auth/login');
      var response = await http.post(
        uri,
        headers: {'Content-Type': 'application/json'},
        body: json.encode({'email': email, 'password': password}),
      );
      
      if (response.statusCode == 200) {
        var data = json.decode(response.body);
        _authToken = data['token'];
        
        // Save token
        SharedPreferences prefs = await SharedPreferences.getInstance();
        await prefs.setString('auth_token', _authToken!);
        
        notifyListeners();
        return true;
      }
      return false;
    } catch (e) {
      print('Login error: $e');
      return false;
    }
  }

  Future<void> logout() async {
    _authToken = null;
    SharedPreferences prefs = await SharedPreferences.getInstance();
    await prefs.remove('auth_token');
    notifyListeners();
  }

  Future<void> loadToken() async {
    SharedPreferences prefs = await SharedPreferences.getInstance();
    _authToken = prefs.getString('auth_token');
    notifyListeners();
  }

  Future<Map<String, dynamic>> detectFireCloud(File imageFile) async {
    try {
      var uri = Uri.parse('$baseUrl/inference/detect');
      var request = http.MultipartRequest('POST', uri);
      
      request.files.add(
        await http.MultipartFile.fromPath(
          'image',
          imageFile.path,
        ),
      );
      
      if (_authToken != null) {
        request.headers['Authorization'] = 'Bearer $_authToken';
      }
      
      var streamedResponse = await request.send();
      var response = await http.Response.fromStream(streamedResponse);
      
      if (response.statusCode == 200) {
        return json.decode(response.body);
      } else {
        throw Exception('Inference failed: ${response.statusCode}');
      }
    } catch (e) {
      print('Cloud inference error: $e');
      return {'status': 'error', 'message': e.toString()};
    }
  }
}