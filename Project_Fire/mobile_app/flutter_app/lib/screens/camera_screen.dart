import 'dart:io';
import 'package:flutter/material.dart';
import 'package:camera/camera.dart';
import 'package:provider/provider.dart';
import '../services/detection_service.dart';
import '../services/api_service.dart';
import '../utils/constants.dart';

class CameraScreen extends StatefulWidget {
  @override
  _CameraScreenState createState() => _CameraScreenState();
}

class _CameraScreenState extends State<CameraScreen> with WidgetsBindingObserver {
  CameraController? _controller;
  List<CameraDescription>? _cameras;
  bool _isDetecting = false;
  bool _fireDetected = false;
  double _confidence = 0.0;
  String _severity = 'low';
  bool _modelLoaded = false;
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _initializeCamera();
  }

  Future<void> _initializeCamera() async {
    try {
      _cameras = await availableCameras();
      _controller = CameraController(_cameras![0], ResolutionPreset.medium);
      
      await _controller!.initialize();
      
      // Cloud model is always "ready"
      _modelLoaded = true;
      
      setState(() {
        _isLoading = false;
      });
    } catch (e) {
      print('Camera initialization error: $e');
      _showErrorDialog('Camera Error', 'Failed to initialize camera: $e');
    }
  }

  Future<void> _scanNow() async {
    if (_isDetecting || _controller == null || !_controller!.value.isInitialized) return;
    
    setState(() {
      _isDetecting = true;
      _fireDetected = false;
    });

    try {
      final XFile image = await _controller!.takePicture();
      final detectionService = Provider.of<DetectionService>(context, listen: false);
      final apiService = Provider.of<ApiService>(context, listen: false);
      
      var result = await detectionService.detectFire(image, apiService);
      
      if (!mounted) return;
      
      if (result['detected'] == true) {
        setState(() {
          _fireDetected = true;
          _confidence = result['confidence'] ?? 0.0;
          _severity = result['severity'] ?? _calculateSeverity(_confidence);
        });
        
        _showFireAlert(result);
      } else {
        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('No fire detected in this frame.')),
        );
      }
    } catch (e) {
      print('Detection error: $e');
      _showErrorDialog('Detection Error', 'Failed to process image: $e');
    } finally {
      if (mounted) {
        setState(() {
          _isDetecting = false;
        });
      }
    }
  }

  String _calculateSeverity(double confidence) {
    if (confidence > 0.9) return 'critical';
    if (confidence > 0.7) return 'high';
    if (confidence > 0.5) return 'medium';
    return 'low';
  }


  void _showFireAlert(Map<String, dynamic> detection) {
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (context) {
        return AlertDialog(
          title: Row(
            children: [
              Icon(Icons.warning, color: Colors.red, size: 30),
              SizedBox(width: 10),
              Text('🔥 FIRE DETECTED!'),
            ],
          ),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text('Confidence: ${(_confidence * 100).toStringAsFixed(1)}%'),
              SizedBox(height: 10),
              LinearProgressIndicator(
                value: _confidence,
                backgroundColor: Colors.grey[300],
                valueColor: AlwaysStoppedAnimation<Color>(
                  _confidence > 0.7 ? Colors.red : Colors.orange,
                ),
              ),
              SizedBox(height: 10),
              Text('Severity: ${(detection['severity'] ?? 'LOW').toUpperCase()}'),
              SizedBox(height: 20),
              Text('📍 Location captured'),
              Text('📸 Image saved and reported'),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () {
                Navigator.of(context).pop();
              },
              child: Text('OK'),
            ),
            TextButton(
              onPressed: () {
                Navigator.of(context).pop();
                Navigator.pushNamed(context, '/dashboard');
              },
              child: Text('View Dashboard'),
            ),
          ],
        );
      },
    );
  }

  void _showErrorDialog(String title, String message) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(title),
        content: Text(message),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: Text('OK'),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return Scaffold(
        body: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              CircularProgressIndicator(),
              SizedBox(height: 20),
              Text('Initializing camera and model...'),
            ],
          ),
        ),
      );
    }

    if (_controller == null || !_controller!.value.isInitialized) {
      return Scaffold(
        body: Center(
          child: Text('Camera not available'),
        ),
      );
    }

    return Scaffold(
      body: Stack(
        children: [
          // Camera preview
          CameraPreview(_controller!),
          
          // Detection overlay
          // Floating Scan Button
          Positioned(
            bottom: 120,
            left: 0,
            right: 0,
            child: Center(
              child: FloatingActionButton.large(
                onPressed: _isDetecting ? null : _scanNow,
                backgroundColor: _isDetecting ? Colors.grey : Colors.red,
                child: _isDetecting 
                  ? CircularProgressIndicator(color: Colors.white)
                  : Icon(Icons.search, size: 40, color: Colors.white),
              ),
            ),
          ),
          
          // Top bar
          Positioned(
            top: 50,
            left: 20,
            child: Container(
              padding: EdgeInsets.symmetric(horizontal: 12, vertical: 6),
              decoration: BoxDecoration(
                color: Colors.black54,
                borderRadius: BorderRadius.circular(20),
              ),
              child: Row(
                children: [
                  Icon(Icons.fiber_manual_record, color: _modelLoaded ? Colors.green : Colors.red, size: 12),
                  SizedBox(width: 5),
                  Text(
                    _modelLoaded ? 'Model Ready' : 'Model Loading...',
                    style: TextStyle(color: Colors.white, fontSize: 12),
                  ),
                ],
              ),
            ),
          ),
          
          // Controls at bottom
          Positioned(
            bottom: 30,
            left: 0,
            right: 0,
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceEvenly,
              children: [
                _buildControlButton(
                  icon: Icons.history,
                  label: 'History',
                  onTap: () => Navigator.pushNamed(context, '/history'),
                ),
                _buildControlButton(
                  icon: Icons.dashboard,
                  label: 'Dashboard',
                  onTap: () => Navigator.pushNamed(context, '/dashboard'),
                ),
                _buildControlButton(
                  icon: Icons.settings,
                  label: 'Settings',
                  onTap: () {},
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildControlButton({
    required IconData icon,
    required String label,
    required VoidCallback onTap,
  }) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: EdgeInsets.symmetric(horizontal: 20, vertical: 10),
        decoration: BoxDecoration(
          color: Colors.black54,
          borderRadius: BorderRadius.circular(25),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, color: Colors.white, size: 20),
            SizedBox(width: 5),
            Text(label, style: TextStyle(color: Colors.white)),
          ],
        ),
      ),
    );
  }


  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _controller?.dispose();
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (_controller == null || !_controller!.value.isInitialized) return;
    
    if (state == AppLifecycleState.inactive) {
      _controller?.dispose();
    } else if (state == AppLifecycleState.resumed) {
      _initializeCamera();
    }
  }
}