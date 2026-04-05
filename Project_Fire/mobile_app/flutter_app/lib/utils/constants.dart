import 'package:flutter/material.dart';

class AppConstants {
  static const String appName = 'Wildfire Detection';
  static const String baseUrl = 'http://10.233.67.51:8000/api';
  
  // Model parameters
  static const int modelInputSize = 320;
  static const double confidenceThreshold = 0.5; 
       
  
  // Colors
  static const Color criticalColor = Color(0xFF8B0000);
  static const Color highColor = Color(0xFFDC3545);
  static const Color mediumColor = Color(0xFFFFC107);
  static const Color lowColor = Color(0xFF28A745);
  
  // SharedPreferences keys
  static const String authTokenKey = 'auth_token';
  static const String userIdKey = 'user_id';
  static const String userEmailKey = 'user_email';
}

class AppStrings {
  static const String fireDetected = '🔥 FIRE DETECTED!';
  static const String loadingModel = 'Loading detection model...';
  static const String cameraError = 'Camera initialization failed';
  static const String locationError = 'Unable to get location';
}