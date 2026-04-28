import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'screens/camera_screen.dart';
import 'screens/login_screen.dart';
import 'screens/dashboard_screen.dart';
import 'screens/history_screen.dart';
import 'screens/landing_screen.dart';
import 'services/detection_service.dart';
import 'services/api_service.dart';
import 'providers/dashboard_provider.dart';

void main() {
  runApp(MyApp());
}

class MyApp extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (_) => DetectionService()),
        ChangeNotifierProvider(create: (_) => ApiService()),
        ChangeNotifierProvider(create: (_) => DashboardProvider()),
      ],
      child: MaterialApp(
        title: 'Wildfire Detection',
        theme: ThemeData(
          primarySwatch: Colors.red,
          visualDensity: VisualDensity.adaptivePlatformDensity,
        ),
        initialRoute: '/landing',
        routes: {
          '/landing': (context) => LandingScreen(),
          '/camera': (context) => CameraScreen(),
          '/login': (context) => LoginScreen(),
          '/dashboard': (context) => DashboardScreen(),
          '/history': (context) => HistoryScreen(),
        },
      ),
    );
  }
}