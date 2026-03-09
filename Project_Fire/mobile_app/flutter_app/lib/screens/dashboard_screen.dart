import 'dart:ui';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../services/api_service.dart';
import '../providers/dashboard_provider.dart';

// UI Constants from Tailwind Mockup
const Color kPrimaryColor = Color(0xFFF48C25);
const Color kBackgroundLight = Color(0xFFF8F7F5);
const Color kBackgroundDark = Color(0xFF221910);
const Color kTextDark = Color(0xFF0F172A); // slate-900

class DashboardScreen extends StatefulWidget {
  @override
  _DashboardScreenState createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _loadData();
    });
  }

  Future<void> _loadData() async {
    final apiService = Provider.of<ApiService>(context, listen: false);
    final dashboardProvider = Provider.of<DashboardProvider>(context, listen: false);
    await dashboardProvider.loadData(apiService);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: kBackgroundLight,
      body: Consumer<DashboardProvider>(
        builder: (context, provider, child) {
          if (provider.isLoading && provider.stats.isEmpty) {
            return Center(child: CircularProgressIndicator(color: kPrimaryColor));
          }

          final activeFires = provider.stats['active_fires']?.toString() ?? '0';
          
          return RefreshIndicator(
            onRefresh: _loadData,
            color: kPrimaryColor,
            child: Stack(
              children: [
                // Scrollable Content
                SingleChildScrollView(
                  physics: AlwaysScrollableScrollPhysics(),
                  child: Padding(
                    padding: const EdgeInsets.only(bottom: 100), // Space for nav
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        _buildHeader(),
                        
                        // Error message if any
                        if (provider.errorMessage != null)
                          Container(
                            margin: EdgeInsets.symmetric(horizontal: 24, vertical: 8),
                            padding: EdgeInsets.all(12),
                            decoration: BoxDecoration(
                              color: Colors.red[50],
                              borderRadius: BorderRadius.circular(12),
                              border: Border.all(color: Colors.red[200]!),
                            ),
                            child: Row(
                              children: [
                                Icon(Icons.error_outline, color: Colors.red, size: 20),
                                SizedBox(width: 8),
                                Expanded(child: Text(provider.errorMessage!, style: TextStyle(color: Colors.red, fontSize: 13))),
                              ],
                            ),
                          ),

                        _buildMapSection(),
                        _buildStatsGrid(activeFires),
                      ],
                    ),
                  ),
                ),
                
                // Custom Bottom Navigation
                Positioned(
                  bottom: 0,
                  left: 0,
                  right: 0,
                  child: _buildBottomNav(context),
                ),
              ],
            ),
          );
        },
      ),
    );
  }

  Widget _buildHeader() {
    return Padding(
      padding: const EdgeInsets.fromLTRB(24, 60, 24, 24),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Row(
            children: [
              Stack(
                children: [
                  Container(
                    width: 48,
                    height: 48,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      border: Border.all(color: kPrimaryColor.withOpacity(0.6), width: 2),
                      image: DecorationImage(
                        image: NetworkImage("https://ui-avatars.com/api/?name=Alex&background=f48c25&color=fff"),
                        fit: BoxFit.cover,
                      ),
                    ),
                  ),
                  Positioned(
                    bottom: 0,
                    right: 0,
                    child: Container(
                      width: 12,
                      height: 12,
                      decoration: BoxDecoration(
                        color: Colors.green[500],
                        shape: BoxShape.circle,
                        border: Border.all(color: Colors.white, width: 2),
                      ),
                    ),
                  ),
                ],
              ),
              SizedBox(width: 12),
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'GOOD MORNING',
                    style: TextStyle(
                      fontSize: 10,
                      fontWeight: FontWeight.w600,
                      letterSpacing: 1.5,
                      color: Colors.blueGrey[500],
                    ),
                  ),
                  Text(
                    'Hello, Alex',
                    style: TextStyle(
                      fontSize: 20,
                      fontWeight: FontWeight.bold,
                      color: kTextDark,
                    ),
                  ),
                ],
              ),
            ],
          ),
          _GlassCard(
            padding: EdgeInsets.all(10),
            borderRadius: 12,
            child: Icon(Icons.notifications_outlined, color: kPrimaryColor),
          ),
        ],
      ),
    );
  }

  Widget _buildMapSection() {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 24),
      child: Container(
        width: double.infinity,
        height: 380,
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(24),
          border: Border.all(color: kPrimaryColor.withOpacity(0.2)),
          color: kPrimaryColor.withOpacity(0.05),
          image: DecorationImage(
            // Fallback map image simulating the thermal/satellite view
            image: NetworkImage("https://images.unsplash.com/photo-1524661135-423995f22d0b?auto=format&fit=crop&q=80&w=800"),
            fit: BoxFit.cover,
            colorFilter: ColorFilter.mode(Colors.black.withOpacity(0.4), BlendMode.darken),
          ),
        ),
        child: Stack(
          children: [
            // Map Gradient Overlay
            Container(
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(24),
                gradient: RadialGradient(
                  colors: [kPrimaryColor.withOpacity(0.1), Colors.transparent],
                  radius: 0.7,
                ),
              ),
            ),
            
            // Map controls (top right)
            Positioned(
              top: 16,
              right: 16,
              child: Column(
                children: [
                  _GlassCard(padding: EdgeInsets.all(8), borderRadius: 8, child: Icon(Icons.layers_outlined, size: 20, color: Colors.white)),
                  SizedBox(height: 8),
                  _GlassCard(padding: EdgeInsets.all(8), borderRadius: 8, child: Icon(Icons.my_location, size: 20, color: Colors.white)),
                ],
              ),
            ),

             // Hotspot Indicator
             Positioned(
              top: 100,
              left: 120,
              child: Column(
                children: [
                  Container(
                    width: 16,
                    height: 16,
                    decoration: BoxDecoration(
                      color: kPrimaryColor,
                      shape: BoxShape.circle,
                      boxShadow: [BoxShadow(color: kPrimaryColor.withOpacity(0.6), blurRadius: 15, spreadRadius: 5)],
                    ),
                    child: Center(child: Container(width: 6, height: 6, decoration: BoxDecoration(color: Colors.white, shape: BoxShape.circle))),
                  ),
                  SizedBox(height: 8),
                  _GlassCard(
                    padding: EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                    borderRadius: 4,
                    child: Text('ACTIVE: ZONE A', style: TextStyle(fontSize: 9, fontWeight: FontWeight.bold, color: kPrimaryColor)),
                  )
                ],
              ),
            ),

            // Scanning Region Footer
            Positioned(
              bottom: 16,
              left: 16,
              right: 16,
              child: _GlassCard(
                padding: EdgeInsets.all(16),
                borderRadius: 16,
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Row(
                      children: [
                        Container(
                          padding: EdgeInsets.all(8),
                          decoration: BoxDecoration(color: kPrimaryColor.withOpacity(0.2), borderRadius: BorderRadius.circular(12)),
                          child: Icon(Icons.radar, color: kPrimaryColor),
                        ),
                        SizedBox(width: 12),
                        Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text('Scanning Region', style: TextStyle(fontSize: 11, fontWeight: FontWeight.w500, color: Colors.blueGrey[600])),
                            Text('Sierra Nevada North', style: TextStyle(fontSize: 14, fontWeight: FontWeight.bold, color: kTextDark)),
                          ],
                        ),
                      ],
                    ),
                    Icon(Icons.arrow_forward_ios, size: 16, color: kPrimaryColor),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildStatsGrid(String activeFires) {
    return Padding(
      padding: const EdgeInsets.all(24),
      child: Column(
        children: [
          // Active Fires Full Width Card
          _GlassCard(
            padding: EdgeInsets.all(20),
            borderRadius: 24,
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('Active Wildfires', style: TextStyle(fontSize: 13, fontWeight: FontWeight.w500, color: Colors.blueGrey[600])),
                    SizedBox(height: 4),
                    Row(
                      crossAxisAlignment: CrossAxisAlignment.end,
                      children: [
                        Text(activeFires, style: TextStyle(fontSize: 32, fontWeight: FontWeight.bold, color: Colors.red[500], height: 1)),
                        SizedBox(width: 6),
                        Padding(
                          padding: const EdgeInsets.only(bottom: 4),
                          child: Text('Critical Zones', style: TextStyle(fontSize: 13, color: Colors.blueGrey[800])),
                        ),
                      ],
                    ),
                  ],
                ),
                Container(
                  padding: EdgeInsets.all(12),
                  decoration: BoxDecoration(color: Colors.red[500]!.withOpacity(0.1), borderRadius: BorderRadius.circular(16)),
                  child: Icon(Icons.local_fire_department, color: Colors.red[500], size: 32),
                ),
              ],
            ),
          ),
          
          SizedBox(height: 16),
          
          // Row of Two Stats
          Row(
            children: [
              Expanded(
                child: _GlassCard(
                  padding: EdgeInsets.all(20),
                  borderRadius: 24,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Container(
                        padding: EdgeInsets.all(8),
                        decoration: BoxDecoration(color: Colors.green[500]!.withOpacity(0.1), borderRadius: BorderRadius.circular(12)),
                        child: Icon(Icons.health_and_safety, color: Colors.green[500]),
                      ),
                      SizedBox(height: 12),
                      Text('Safe Zones', style: TextStyle(fontSize: 11, fontWeight: FontWeight.w500, color: Colors.blueGrey[600])),
                      Text('94.2%', style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold, color: kTextDark)),
                    ],
                  ),
                ),
              ),
              SizedBox(width: 16),
              Expanded(
                child: _GlassCard(
                  padding: EdgeInsets.all(20),
                  borderRadius: 24,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Container(
                        padding: EdgeInsets.all(8),
                        decoration: BoxDecoration(color: kPrimaryColor.withOpacity(0.1), borderRadius: BorderRadius.circular(12)),
                        child: Icon(Icons.air, color: kPrimaryColor),
                      ),
                      SizedBox(height: 12),
                      Text('Air Quality', style: TextStyle(fontSize: 11, fontWeight: FontWeight.w500, color: Colors.blueGrey[600])),
                      Row(
                        crossAxisAlignment: CrossAxisAlignment.end,
                        children: [
                          Text('Moderate', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: kTextDark)),
                          SizedBox(width: 4),
                          Text('42', style: TextStyle(fontSize: 12, color: kPrimaryColor)),
                        ],
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildBottomNav(BuildContext context) {
    return _GlassCard(
      borderRadius: 0,
      padding: EdgeInsets.only(top: 16, bottom: 32, left: 24, right: 24),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          _buildNavItem(Icons.grid_view, 'DASHBOARD', true, () {}),
          _buildNavItem(Icons.map_outlined, 'EXPLORER', false, () {}),
          
          // Center Big Primary Button
          GestureDetector(
            onTap: () => Navigator.pushNamed(context, '/camera'),
            child: Container(
              margin: EdgeInsets.only(bottom: 24),
              width: 56,
              height: 56,
              decoration: BoxDecoration(
                color: kPrimaryColor,
                shape: BoxShape.circle,
                boxShadow: [BoxShadow(color: kPrimaryColor.withOpacity(0.4), blurRadius: 15, offset: Offset(0, 8))],
              ),
              child: Icon(Icons.add, color: kBackgroundDark, size: 32),
            ),
          ),
          
          _buildNavItem(Icons.history, 'HISTORY', false, () => Navigator.pushNamed(context, '/history')),
          _buildNavItem(Icons.settings_outlined, 'SYSTEM', false, () {}),
        ],
      ),
    );
  }

  Widget _buildNavItem(IconData icon, String label, bool isActive, VoidCallback onTap) {
    return GestureDetector(
      onTap: onTap,
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, color: isActive ? kPrimaryColor : Colors.blueGrey[400]),
          SizedBox(height: 4),
          Text(
            label,
            style: TextStyle(
              fontSize: 9,
              fontWeight: FontWeight.bold,
               color: isActive ? kPrimaryColor : Colors.blueGrey[400],
            ),
          ),
        ],
      ),
    );
  }
}

// Reusable Glassmorphism Card
class _GlassCard extends StatelessWidget {
  final Widget child;
  final EdgeInsets padding;
  final double borderRadius;

  const _GlassCard({required this.child, required this.padding, required this.borderRadius});

  @override
  Widget build(BuildContext context) {
    return ClipRRect(
      borderRadius: BorderRadius.circular(borderRadius),
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: 12, sigmaY: 12),
        child: Container(
          padding: padding,
          decoration: BoxDecoration(
            color: Colors.white.withOpacity(0.8),
            borderRadius: BorderRadius.circular(borderRadius),
            border: Border.all(color: kPrimaryColor.withOpacity(0.2)),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withOpacity(0.05),
                blurRadius: 6,
                offset: Offset(0, 4),
              )
            ],
          ),
          child: child,
        ),
      ),
    );
  }
}