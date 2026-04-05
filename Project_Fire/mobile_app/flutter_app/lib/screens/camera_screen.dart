import 'dart:async';
import 'dart:io';
import 'dart:ui';
import 'package:flutter/material.dart';
import 'package:camera/camera.dart';
import 'package:provider/provider.dart';
import '../services/detection_service.dart';
import '../services/api_service.dart';

// UI Constants from Tailwind Mockup
const Color kPrimaryColor = Color(0xFFF48C25);
const Color kBackgroundLight = Color(0xFFF8F7F5);
const Color kBackgroundDark = Color(0xFF221910);
const Color kTextDark = Color(0xFF1A1A2E);
const Color kSuccessGreen = Color(0xFF22C55E);
const Color kAlertRed = Color(0xFFEF4444);
const Color kEmergencyRed = Color(0xFFDC2626);

class CameraScreen extends StatefulWidget {
  @override
  _CameraScreenState createState() => _CameraScreenState();
}

class _CameraScreenState extends State<CameraScreen> with WidgetsBindingObserver, SingleTickerProviderStateMixin {
  CameraController? _controller;
  List<CameraDescription>? _cameras;
  bool _isDetecting = false;
  bool _fireDetected = false;
  double _confidence = 0.0;
  String _severity = 'low';
  bool _modelLoaded = false;
  bool _isLoading = true;
  
  late AnimationController _scannerAnimationController;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _initializeCamera();
    
    _scannerAnimationController = AnimationController(
        vsync: this, duration: Duration(seconds: 2))..repeat(reverse: true);
        
    // Start real-time surveillance loop
    _startSurveillanceLoop();
  }

  void _startSurveillanceLoop() {
    // Attempt an automated scan every 2 seconds in the background
    Timer.periodic(Duration(seconds: 2), (timer) {
      if (mounted && _controller != null && _controller!.value.isInitialized && !_isDetecting) {
        _scanNow(silent: true);
      }
    });
  }

  Future<void> _initializeCamera() async {
    try {
      _cameras = await availableCameras();
      _controller = CameraController(_cameras![0], ResolutionPreset.high, enableAudio: false);
      
      await _controller!.initialize();
      _modelLoaded = true;
      
      setState(() {
        _isLoading = false;
      });
    } catch (e) {
      print('Camera initialization error: $e');
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
      
      // Step 1: Run AI inference
      var result = await detectionService.detectFire(image, apiService);
      
      if (!mounted) return;
      
      if (result['detected'] == true) {
        final double confidence = (result['confidence'] ?? 0.0).toDouble();
        final String severity = result['severity'] ?? _calculateSeverity(confidence);

        setState(() {
          _fireDetected = true;
          _confidence = confidence;
          _severity = severity;
        });

        // Step 2: Report fire to backend
        try {
          await apiService.reportDetection(
            detection: {
              'confidence': confidence,
              'severity': severity,
              'timestamp': DateTime.now().toIso8601String(),
            },
            imageFile: File(image.path),
          );
        } catch (reportError) {
          print('⚠️ Fire detected but failed to report: $reportError');
        }
        
        _showFireAlert(result, image.path);
      } else {
        if (!mounted || silent) return;
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('No fire detected in this frame.', style: TextStyle(fontWeight: FontWeight.bold)),
            backgroundColor: kTextDark,
            behavior: SnackBarBehavior.floating,
          ),
        );
      }
    } catch (e) {
      print('Detection error: $e');
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

  void _showFireAlert(Map<String, dynamic> detection, String imagePath) {
    showGeneralDialog(
      context: context,
      barrierDismissible: false,
      barrierColor: kBackgroundDark.withOpacity(0.9),
      transitionDuration: Duration(milliseconds: 300),
      pageBuilder: (context, anim1, anim2) {
        return Scaffold(
          backgroundColor: Colors.white,
          body: Column(
            children: [
              // Header
              Container(
                padding: EdgeInsets.only(top: 50, left: 16, right: 16, bottom: 16),
                decoration: BoxDecoration(color: Colors.white, border: Border(bottom: BorderSide(color: Colors.grey[200]!))),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    IconButton(icon: Icon(Icons.arrow_back), onPressed: () => Navigator.pop(context)),
                    Text('EMERGENCY DASHBOARD', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16, letterSpacing: 1)),
                    IconButton(icon: Icon(Icons.share_outlined), onPressed: () {}),
                  ],
                ),
              ),
              
              Expanded(
                child: SingleChildScrollView(
                  child: Column(
                    children: [
                      // Image with glowing border
                      Container(
                        margin: EdgeInsets.all(16),
                        height: 220,
                        decoration: BoxDecoration(
                          borderRadius: BorderRadius.circular(16),
                          border: Border.all(color: kEmergencyRed, width: 2),
                          boxShadow: [
                            BoxShadow(color: kEmergencyRed.withOpacity(0.4), blurRadius: 20, spreadRadius: 0),
                          ],
                          image: DecorationImage(image: FileImage(File(imagePath)), fit: BoxFit.cover),
                        ),
                        child: Stack(
                          children: [
                            Container(
                              decoration: BoxDecoration(
                                borderRadius: BorderRadius.circular(16),
                                gradient: LinearGradient(begin: Alignment.bottomCenter, end: Alignment.topCenter, colors: [kBackgroundDark.withOpacity(0.8), Colors.transparent]),
                              ),
                            ),
                            Positioned(
                              bottom: 12,
                              left: 12,
                              child: Container(
                                padding: EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                                decoration: BoxDecoration(color: kEmergencyRed.withOpacity(0.9), borderRadius: BorderRadius.circular(20)),
                                child: Row(
                                  children: [
                                    Container(width: 8, height: 8, decoration: BoxDecoration(color: Colors.white, shape: BoxShape.circle)),
                                    SizedBox(width: 8),
                                    Text('LIVE FEED: DRONE-04', style: TextStyle(color: Colors.white, fontSize: 10, fontWeight: FontWeight.bold, letterSpacing: 1)),
                                  ],
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),
                      
                      // Critical Alert Banner
                      Padding(
                        padding: const EdgeInsets.symmetric(horizontal: 16),
                        child: Container(
                          width: double.infinity,
                          padding: EdgeInsets.all(24),
                          decoration: BoxDecoration(
                            color: kEmergencyRed,
                            borderRadius: BorderRadius.circular(16),
                            boxShadow: [BoxShadow(color: kEmergencyRed.withOpacity(0.2), blurRadius: 10, offset: Offset(0, 4))],
                          ),
                          child: Column(
                            children: [
                              Text('CRITICAL FIRE ALERT', style: TextStyle(color: Colors.white, fontSize: 24, fontWeight: FontWeight.bold, letterSpacing: -0.5)),
                              SizedBox(height: 4),
                              Text('Immediate Evacuation Recommended for Nearby Zones', style: TextStyle(color: Colors.white.withOpacity(0.9), fontSize: 12, fontWeight: FontWeight.w500), textAlign: TextAlign.center),
                            ],
                          ),
                        ),
                      ),
                      
                      // Data Grid
                      Padding(
                        padding: const EdgeInsets.all(16),
                        child: Row(
                          children: [
                            Expanded(child: _buildAlertStatCard('Severity', _severity.toUpperCase(), kEmergencyRed)),
                            SizedBox(width: 16),
                            Expanded(child: _buildAlertStatCard('Confidence', '${(_confidence * 100).toStringAsFixed(0)}%', kTextDark)),
                          ],
                        ),
                      ),
                      
                      // Location
                      Padding(
                        padding: const EdgeInsets.symmetric(horizontal: 16),
                        child: Container(
                          padding: EdgeInsets.all(16),
                          decoration: BoxDecoration(color: Colors.orange[50], border: Border.all(color: Colors.orange[100]!), borderRadius: BorderRadius.circular(16)),
                          child: Row(
                            children: [
                              Container(padding: EdgeInsets.all(8), decoration: BoxDecoration(color: kPrimaryColor.withOpacity(0.2), borderRadius: BorderRadius.circular(8)), child: Icon(Icons.location_on, color: kPrimaryColor)),
                              SizedBox(width: 16),
                              Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text('LOCATION', style: TextStyle(color: kPrimaryColor, fontSize: 10, fontWeight: FontWeight.bold, letterSpacing: 1)),
                                  Text('Sierra Nevada', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: kTextDark)),
                                ],
                              ),
                            ],
                          ),
                        ),
                      ),
                      
                      SizedBox(height: 32),
                      
                      // Action Buttons
                      Padding(
                        padding: const EdgeInsets.symmetric(horizontal: 16),
                        child: ElevatedButton.icon(
                          onPressed: () {},
                          icon: Icon(Icons.call, color: Colors.white),
                          label: Text('Call Emergency Services', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: Colors.white)),
                          style: ElevatedButton.styleFrom(
                            backgroundColor: kEmergencyRed,
                            minimumSize: Size(double.infinity, 56),
                            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                            elevation: 0,
                          ),
                        ),
                      ),
                      SizedBox(height: 12),
                      Padding(
                        padding: const EdgeInsets.symmetric(horizontal: 16),
                        child: OutlinedButton.icon(
                          onPressed: () {
                            Navigator.pop(context);
                            Navigator.pushReplacementNamed(context, '/dashboard');
                          },
                          icon: Icon(Icons.map, color: kPrimaryColor),
                          label: Text('View on Map', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: kTextDark)),
                          style: OutlinedButton.styleFrom(
                            side: BorderSide(color: Colors.grey[300]!, width: 2),
                            minimumSize: Size(double.infinity, 56),
                            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                          ),
                        ),
                      ),
                      SizedBox(height: 40),
                    ],
                  ),
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  Widget _buildAlertStatCard(String title, String value, Color valueColor) {
    return Container(
      padding: EdgeInsets.all(16),
      decoration: BoxDecoration(color: Colors.orange[50], border: Border.all(color: Colors.orange[100]!), borderRadius: BorderRadius.circular(16)),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title.toUpperCase(), style: TextStyle(color: kPrimaryColor, fontSize: 10, fontWeight: FontWeight.bold, letterSpacing: 1)),
          SizedBox(height: 4),
          Text(value, style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold, color: valueColor)),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading || _controller == null || !_controller!.value.isInitialized) {
      return Scaffold(backgroundColor: kBackgroundDark, body: Center(child: CircularProgressIndicator(color: kPrimaryColor)));
    }

    return Scaffold(
      backgroundColor: Colors.black,
      body: Stack(
        fit: StackFit.expand,
        children: [
          // 1. Full Screen Camera Feed
          CameraPreview(_controller!),
          
          // 2. HUD Overlay Gradient
          Container(
            decoration: BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.topCenter,
                end: Alignment.bottomCenter,
                colors: [Colors.white.withOpacity(0.9), Colors.transparent, Colors.white.withOpacity(0.4)],
                stops: [0.0, 0.2, 1.0],
              ),
            ),
          ),
          
          // 3. Top Header
          Positioned(
            top: 50, left: 24, right: 24,
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                _GlassIconButton(icon: Icons.arrow_back_ios_new, onTap: () => Navigator.pop(context)),
                Column(
                  children: [
                    Text('AEROSCAN V2.4', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16, letterSpacing: 2, color: kTextDark)),
                    Row(
                      children: [
                        Container(width: 8, height: 8, decoration: BoxDecoration(color: kSuccessGreen, shape: BoxShape.circle, boxShadow: [BoxShadow(color: kSuccessGreen, blurRadius: 8)])),
                        SizedBox(width: 8),
                        Text('SYSTEM ONLINE', style: TextStyle(fontSize: 10, fontWeight: FontWeight.w600, color: Colors.blueGrey[600], letterSpacing: 1)),
                      ],
                    ),
                  ],
                ),
                _GlassIconButton(icon: Icons.settings, onTap: () {}),
              ],
            ),
          ),
          
          // 4. Center Bounding Box Scanner
          Center(
            child: Container(
              width: 280,
              height: 380,
              decoration: BoxDecoration(
                border: Border.all(color: kPrimaryColor, width: 2),
                borderRadius: BorderRadius.circular(12),
                boxShadow: [
                  BoxShadow(color: kPrimaryColor.withOpacity(0.1), blurRadius: 20),
                  BoxShadow(color: kPrimaryColor.withOpacity(0.1), blurRadius: 10),
                ],
              ),
              child: Stack(
                children: [
                  // Corner thick borders
                  _buildCorner(top: -2, left: -2, border: Border(top: BorderSide(color: kPrimaryColor, width: 4), left: BorderSide(color: kPrimaryColor, width: 4))),
                  _buildCorner(top: -2, right: -2, border: Border(top: BorderSide(color: kPrimaryColor, width: 4), right: BorderSide(color: kPrimaryColor, width: 4))),
                  _buildCorner(bottom: -2, left: -2, border: Border(bottom: BorderSide(color: kPrimaryColor, width: 4), left: BorderSide(color: kPrimaryColor, width: 4))),
                  _buildCorner(bottom: -2, right: -2, border: Border(bottom: BorderSide(color: kPrimaryColor, width: 4), right: BorderSide(color: kPrimaryColor, width: 4))),
                  
                  // Animated Scanner Line
                  if (_isDetecting)
                    AnimatedBuilder(
                      animation: _scannerAnimationController,
                      builder: (context, child) {
                        return Positioned(
                          top: _scannerAnimationController.value * 370,
                          left: 0,
                          right: 0,
                          child: Container(
                            height: 2,
                            decoration: BoxDecoration(
                              gradient: LinearGradient(colors: [Colors.transparent, kPrimaryColor, Colors.transparent]),
                              boxShadow: [BoxShadow(color: kPrimaryColor, blurRadius: 15, spreadRadius: 2)],
                            ),
                          ),
                        );
                      },
                    ),
                    
                  // Floating AI Data Panel
                  if (_isDetecting)
                    Positioned(
                      bottom: 24, left: 24, right: 24,
                      child: ClipRRect(
                        borderRadius: BorderRadius.circular(16),
                        child: BackdropFilter(
                          filter: ImageFilter.blur(sigmaX: 12, sigmaY: 12),
                          child: Container(
                            padding: EdgeInsets.all(16),
                            decoration: BoxDecoration(color: Colors.white.withOpacity(0.7), border: Border.all(color: kPrimaryColor.withOpacity(0.3)), borderRadius: BorderRadius.circular(16)),
                            child: Row(
                              mainAxisAlignment: MainAxisAlignment.spaceBetween,
                              children: [
                                Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  mainAxisSize: MainAxisSize.min,
                                  children: [
                                    Text('Scanning in progress...', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13, color: kTextDark)),
                                    SizedBox(height: 4),
                                    Row(
                                      children: [
                                        SizedBox(
                                          width: 90,
                                          height: 6,
                                          child: ClipRRect(
                                            borderRadius: BorderRadius.circular(10),
                                            child: LinearProgressIndicator(value: null, backgroundColor: kPrimaryColor.withOpacity(0.2), valueColor: AlwaysStoppedAnimation<Color>(kPrimaryColor)),
                                          ),
                                        ),
                                        SizedBox(width: 8),
                                        Text('CONFIDENCE: --%', style: TextStyle(color: kPrimaryColor, fontSize: 10, fontWeight: FontWeight.bold, letterSpacing: 0.5)),
                                      ],
                                    ),
                                  ],
                                ),
                                Icon(Icons.biotech, color: kPrimaryColor),
                              ],
                            ),
                          ),
                        ),
                      ),
                    ),
                ],
              ),
            ),
          ),
          
          // 5. Bottom Controls
          Positioned(
            bottom: 40, left: 0, right: 0,
            child: Column(
              children: [
                // Quick Environment Stats
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 40),
                  child: Row(
                    children: [
                      Expanded(child: _buildEnvStat('TEMP', '28°C')),
                      SizedBox(width: 16),
                      Expanded(child: _buildEnvStat('HUMIDITY', '14%', isAlert: true)),
                      SizedBox(width: 16),
                      Expanded(child: _buildEnvStat('WIND', '12km/h')),
                    ],
                  ),
                ),
                SizedBox(height: 30),
                
                // Huge Scan Button
                GestureDetector(
                  onTap: _isDetecting ? null : _scanNow,
                  child: Stack(
                    alignment: Alignment.center,
                    children: [
                      if (_isDetecting) Container(width: 96, height: 96, decoration: BoxDecoration(shape: BoxShape.circle, border: Border.all(color: kPrimaryColor.withOpacity(0.2), width: 2))),
                      Container(width: 112, height: 112, decoration: BoxDecoration(shape: BoxShape.circle, border: Border.all(color: kPrimaryColor.withOpacity(0.1), width: 1))),
                      AnimatedContainer(
                        duration: Duration(milliseconds: 200),
                        width: _isDetecting ? 70 : 80,
                        height: _isDetecting ? 70 : 80,
                        decoration: BoxDecoration(
                          color: _isDetecting ? Colors.grey[400] : kPrimaryColor,
                          shape: BoxShape.circle,
                          boxShadow: _isDetecting ? [] : [BoxShadow(color: kPrimaryColor.withOpacity(0.5), blurRadius: 30)],
                        ),
                        child: Icon(Icons.local_fire_department, color: kBackgroundDark, size: 40),
                      ),
                      Positioned(
                        bottom: -24,
                        child: Text(
                          _isDetecting ? 'SCANNING...' : 'TAP TO SCAN',
                          style: TextStyle(color: kPrimaryColor, fontSize: 10, fontWeight: FontWeight.bold, letterSpacing: 2),
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildCorner({double? top, double? bottom, double? left, double? right, required Border border}) {
    return Positioned(
      top: top, bottom: bottom, left: left, right: right,
      child: Container(width: 20, height: 20, decoration: BoxDecoration(border: border)),
    );
  }

  Widget _buildEnvStat(String label, String value, {bool isAlert = false}) {
    return ClipRRect(
      borderRadius: BorderRadius.circular(12),
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: 10, sigmaY: 10),
        child: Container(
          padding: EdgeInsets.symmetric(vertical: 12),
          decoration: BoxDecoration(
            color: Colors.white.withOpacity(0.7),
            border: Border.all(color: isAlert ? kAlertRed.withOpacity(0.3) : kPrimaryColor.withOpacity(0.2)),
            borderRadius: BorderRadius.circular(12),
          ),
          child: Column(
            children: [
              Text(label, style: TextStyle(fontSize: 9, fontWeight: FontWeight.bold, color: Colors.blueGrey[500], letterSpacing: 1)),
              SizedBox(height: 2),
              Text(value, style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: kTextDark)),
            ],
          ),
        ),
      ),
    );
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _scannerAnimationController.dispose();
    _controller?.dispose();
    super.dispose();
  }
}

class _GlassIconButton extends StatelessWidget {
  final IconData icon;
  final VoidCallback onTap;
  const _GlassIconButton({required this.icon, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: ClipRRect(
        borderRadius: BorderRadius.circular(20),
        child: BackdropFilter(
          filter: ImageFilter.blur(sigmaX: 12, sigmaY: 12),
          child: Container(
            padding: EdgeInsets.all(10),
            decoration: BoxDecoration(color: Colors.white.withOpacity(0.7), border: Border.all(color: kPrimaryColor.withOpacity(0.3)), shape: BoxShape.circle),
            child: Icon(icon, color: kTextDark, size: 20),
          ),
        ),
      ),
    );
  }
}