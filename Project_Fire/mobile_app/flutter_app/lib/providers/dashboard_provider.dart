import 'package:flutter/material.dart';
import '../services/api_service.dart';

class DashboardProvider extends ChangeNotifier {
  Map<String, dynamic> _stats = {};
  List<dynamic> _recentDetections = [];
  bool _isLoading = false;
  String? _errorMessage;

  Map<String, dynamic> get stats => _stats;
  List<dynamic> get recentDetections => _recentDetections;
  bool get isLoading => _isLoading;
  String? get errorMessage => _errorMessage;

  Future<void> loadData(ApiService apiService) async {
    _isLoading = true;
    _errorMessage = null;
    // Notify listeners so UI shows loading indicator immediately
    notifyListeners();
    
    try {
      _stats = await apiService.getStats();
      _recentDetections = await apiService.getDetections(limit: 10);
    } catch (e) {
      _errorMessage = 'Failed to load dashboard data. Please check your connection.';
      print('DashboardProvider Error: $e');
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  void clearError() {
    _errorMessage = null;
    notifyListeners();
  }
}
