import 'dart:io';
import 'dart:async';
import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:camera/camera.dart';
import 'package:provider/provider.dart';
import 'package:image_picker/image_picker.dart';
import 'package:location/location.dart';
import '../services/api_service.dart';
import '../services/detection_service.dart';
import '../utils/constants.dart';

const kBackgroundDark = Color(0xFF0D1117);
const kPrimary = Color(0xFFFF4C4C);
const kTextDark = Color(0xFF1E1E1E);

class CameraScreen extends StatefulWidget {
  @override
  _CameraScreenState createState() => _CameraScreenState();
}

class _CameraScreenState extends State<CameraScreen> {
  CameraController? _controller;
  List<CameraDescription>? _cameras;
  bool _isInitialized = false;
  bool _isProcessing = false;
  bool _isLiveActive = false;
  Timer? _liveTimer;
  final ImagePicker _picker = ImagePicker();
  final Location _location = Location();

  @override
  void initState() {
    super.initState();
    _initScanner();
    _initLocation();
  }

  Future<void> _initLocation() async {
    bool _serviceEnabled;
    PermissionStatus _permissionGranted;

    _serviceEnabled = await _location.serviceEnabled();
    if (!_serviceEnabled) {
      _serviceEnabled = await _location.requestService();
      if (!_serviceEnabled) return;
    }

    _permissionGranted = await _location.hasPermission();
    if (_permissionGranted == PermissionStatus.denied) {
      _permissionGranted = await _location.requestPermission();
      if (_permissionGranted != PermissionStatus.granted) return;
    }
  }

  Future<void> _initScanner() async {
    try {
      _cameras = await availableCameras();
      if (_cameras != null && _cameras!.isNotEmpty) {
        _controller = CameraController(_cameras![0], ResolutionPreset.high);
        await _controller!.initialize();
        if (mounted) setState(() { _isInitialized = true; });
      }
    } catch (e) {
      print("Camera init error: $e");
    }
  }

  Future<void> _pickAndAnalyze() async {
    final XFile? pickedFile = await _picker.pickImage(source: ImageSource.gallery);
    if (pickedFile != null) {
      _runAnalysis(pickedFile);
    }
  }

  void _toggleLiveMode() {
    setState(() { _isLiveActive = !_isLiveActive; });
    
    if (_isLiveActive) {
      _liveTimer = Timer.periodic(Duration(seconds: 4), (timer) {
        if (!_isProcessing && mounted) {
          _captureAndAnalyze(silent: true);
        }
      });
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('📡 Live AI Surveillance Started'), backgroundColor: kPrimary));
    } else {
      _liveTimer?.cancel();
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('⏹️ Surveillance Stopped'), backgroundColor: Colors.blueGrey));
    }
  }

  Future<void> _captureAndAnalyze({bool silent = false}) async {
    if (_controller == null || !_controller!.value.isInitialized || _isProcessing) return;
    XFile image = await _controller!.takePicture();
    _runAnalysis(image, silent: silent);
  }

  Future<void> _runAnalysis(XFile xFile, {bool silent = false}) async {
    setState(() { _isProcessing = true; });
    try {
      // 📍 FETCH LOCATION — with Windows/Web fallback
      LocationData? loc;
      if (!kIsWeb) {
        try {
          loc = await _location.getLocation().timeout(Duration(seconds: 10));
          print("📍 GPS: ${loc.latitude}, ${loc.longitude}");
        } catch (e) {
          print("Location timeout or error: $e");
        }
      }

      final apiService = Provider.of<ApiService>(context, listen: false);
      final detectionService = Provider.of<DetectionService>(context, listen: false);

      final double lat = loc?.latitude ?? 0.0;
      final double lng = loc?.longitude ?? 0.0;

      if (lat == 0.0 && lng == 0.0 && !silent) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('⚠️ GPS unavailable — sending without location.'),
            backgroundColor: Colors.orange,
            duration: Duration(seconds: 2),
          ),
        );
      }

      final result = await detectionService.detectFire(
        xFile,
        apiService,
        lat: lat,
        lng: lng,
      );

      if (result['status'] == 'error' || result.containsKey('error')) {
        if (!silent) {
          ScaffoldMessenger.of(context).showSnackBar(SnackBar(
            content: Text('❌ Error: Could not connect to Backend. Check Wi-Fi / IP.'),
            backgroundColor: Colors.red,
          ));
        }
      } else if (result['fire_detected'] == true) {
        _showFireDialog(result, xFile.path);
        if (silent) {
          ScaffoldMessenger.of(context).showSnackBar(SnackBar(
            content: Text('🔥 Fire Detected! Pinned to Global Map.'),
            backgroundColor: kPrimary,
          ));
        }
      } else if (!silent) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text('✅ Clean Frame: No fire detected.'),
          backgroundColor: Colors.green,
        ));
      }
    } catch (e) {
      if (!silent) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text('❌ Error: Backend Offline or Invalid IP'),
          backgroundColor: Colors.red,
        ));
      }
    } finally {
      if (mounted) setState(() { _isProcessing = false; });
    }
  }

  void _showFireDialog(Map<String, dynamic> result, String imagePath) {
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (context) => AlertDialog(
        title: Text('🚨 FIRE SIGNAL!', style: TextStyle(color: kPrimary, fontWeight: FontWeight.bold)),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            ClipRRect(
              borderRadius: BorderRadius.circular(8),
              child: kIsWeb
                ? Icon(Icons.local_fire_department, size: 100, color: kPrimary)
                : Image.file(File(imagePath), height: 180),
            ),
            SizedBox(height: 10),
            Text('Confidence: ${(((result['confidence'] ?? 0) as num) * 100).toStringAsFixed(1)}%'),
            Text('Pinned to Global Dashboard Map.', style: TextStyle(fontSize: 10, color: Colors.grey)),
          ],
        ),
        actions: [
          ElevatedButton(onPressed: () => Navigator.pop(context), child: Text('OK')),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: kBackgroundDark,
      body: Stack(
        children: [
          Positioned.fill(
            child: _isInitialized ? CameraPreview(_controller!) : Center(child: CircularProgressIndicator(color: kPrimary)),
          ),
          Positioned(
            bottom: 0, left: 0, right: 0,
            child: Container(
              padding: EdgeInsets.symmetric(vertical: 40, horizontal: 30),
              decoration: BoxDecoration(gradient: LinearGradient(begin: Alignment.topCenter, end: Alignment.bottomCenter, colors: [Colors.transparent, Colors.black.withOpacity(0.8)])),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  if (_isLiveActive) 
                    Padding(padding: EdgeInsets.only(bottom: 20), child: Text('📡 LIVE SURVEILLANCE ACTIVE', style: TextStyle(color: kPrimary, fontWeight: FontWeight.bold, fontSize: 12))),
                  
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                    children: [
                      _actionIcon(Icons.photo_library, "UPLOAD", _pickAndAnalyze),
                      GestureDetector(
                        onTap: () => _captureAndAnalyze(),
                        child: Container(
                          padding: EdgeInsets.all(20),
                          decoration: BoxDecoration(color: _isProcessing ? Colors.blueGrey : kPrimary, shape: BoxShape.circle, boxShadow: [BoxShadow(color: kPrimary.withOpacity(0.4), blurRadius: 20)]),
                          child: Icon(_isProcessing ? Icons.sync : Icons.camera_alt, color: Colors.white, size: 36),
                        ),
                      ),
                      _actionIcon(_isLiveActive ? Icons.videocam_off : Icons.videocam, "LIVE AI", _toggleLiveMode),
                    ],
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _actionIcon(IconData icon, String label, VoidCallback onTap) {
    return Column(
      children: [
        IconButton(icon: Icon(icon, color: Colors.white, size: 30), onPressed: onTap),
        Text(label, style: TextStyle(color: Colors.white, fontSize: 10, fontWeight: FontWeight.bold)),
      ],
    );
  }

  @override
  void dispose() {
    _liveTimer?.cancel();
    _controller?.dispose();
    super.dispose();
  }
}