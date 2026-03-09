import 'dart:ui';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../services/api_service.dart';
import 'package:intl/intl.dart';

// UI Constants from Tailwind Mockup
const Color kPrimaryColor = Color(0xFF137FEC); // New blue primary from History mockup
const Color kDashboardPrimary = Color(0xFFF48C25); // Original orange
const Color kBackgroundLight = Color(0xFFF6F7F8);
const Color kBackgroundDark = Color(0xFF101922);
const Color kSeverityCritical = Color(0xFFEF4444);
const Color kSeverityMedium = Color(0xFFF59E0B);
const Color kSeverityLow = Color(0xFF10B981);
const Color kTextDark = Color(0xFF0F172A);

class HistoryScreen extends StatefulWidget {
  @override
  _HistoryScreenState createState() => _HistoryScreenState();
}

class _HistoryScreenState extends State<HistoryScreen> {
  String _activeTab = 'All';

  @override
  Widget build(BuildContext context) {
    final apiService = Provider.of<ApiService>(context);

    // Using the original dashboard orange for consistency across the app,
    // even though the specific History HTML mockup used blue.
    final Color activeColor = kDashboardPrimary;

    return Scaffold(
      backgroundColor: kBackgroundLight,
      body: Stack(
        children: [
          // Main Scrollable Area
          Column(
            children: [
              // Header
              Container(
                padding: const EdgeInsets.fromLTRB(16, 60, 16, 16),
                decoration: BoxDecoration(
                  color: kBackgroundLight.withOpacity(0.9),
                ),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    IconButton(
                      icon: Icon(Icons.arrow_back, color: Colors.blueGrey[700]),
                      onPressed: () => Navigator.pop(context),
                      style: IconButton.styleFrom(backgroundColor: Colors.blueGrey[100]?.withOpacity(0.5)),
                    ),
                    Text(
                      'History',
                      style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold, color: kTextDark, letterSpacing: -0.5),
                    ),
                    IconButton(
                      icon: Icon(Icons.search, color: Colors.blueGrey[700]),
                      onPressed: () {},
                      style: IconButton.styleFrom(backgroundColor: Colors.blueGrey[100]?.withOpacity(0.5)),
                    ),
                  ],
                ),
              ),
              
              // Tabs
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 24),
                child: Row(
                  children: [
                    _buildTab('All', activeColor),
                    SizedBox(width: 24),
                    _buildTab('Critical', activeColor),
                    SizedBox(width: 24),
                    _buildTab('Recent', activeColor),
                  ],
                ),
              ),
              
              Divider(height: 1, color: Colors.grey[300]),
              
              // List Content
              Expanded(
                child: FutureBuilder<List<dynamic>>(
                  future: apiService.getDetections(limit: 20),
                  builder: (context, snapshot) {
                    if (snapshot.connectionState == ConnectionState.waiting) {
                      return Center(child: CircularProgressIndicator(color: activeColor));
                    }
                    
                    if (snapshot.hasError || snapshot.data == null) {
                      return Center(child: Text('Error loading history', style: TextStyle(color: Colors.red)));
                    }

                    final allItems = snapshot.data!;
                    List<dynamic> items = allItems;
                    
                    // Basic client-side filtering based on tab
                    if (_activeTab == 'Critical') {
                      items = allItems.where((i) => i['severity']?.toString().toLowerCase() == 'critical').toList();
                    }
                    
                    if (items.isEmpty) {
                      return Center(
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Icon(Icons.history, size: 64, color: Colors.grey[400]),
                            SizedBox(height: 16),
                            Text('No detections found', style: TextStyle(color: Colors.grey[600], fontWeight: FontWeight.w500)),
                          ],
                        ),
                      );
                    }

                    return RefreshIndicator(
                      color: activeColor,
                      onRefresh: () async {
                        setState(() {});
                      },
                      child: ListView.builder(
                        padding: EdgeInsets.only(top: 16, bottom: 100, left: 24, right: 24),
                        itemCount: items.length,
                        itemBuilder: (context, index) {
                          final item = items[index];
                          return _buildHistoryCard(item);
                        },
                      ),
                    );
                  },
                ),
              ),
            ],
          ),
          
          // Custom Bottom Navigation
          Positioned(
            bottom: 0,
            left: 0,
            right: 0,
            child: _buildBottomNav(context, activeColor),
          ),
        ],
      ),
    );
  }

  Widget _buildTab(String title, Color activeColor) {
    bool isActive = _activeTab == title;
    return GestureDetector(
      onTap: () {
        setState(() {
          _activeTab = title;
        });
      },
      child: Container(
        padding: EdgeInsets.only(bottom: 12),
        decoration: BoxDecoration(
          border: Border(
            bottom: BorderSide(
              color: isActive ? activeColor : Colors.transparent,
              width: 2,
            ),
          ),
        ),
        child: Text(
          title,
          style: TextStyle(
            fontSize: 14,
            fontWeight: isActive ? FontWeight.bold : FontWeight.w600,
            color: isActive ? activeColor : Colors.blueGrey[400],
          ),
        ),
      ),
    );
  }

  Widget _buildHistoryCard(Map<String, dynamic> item) {
    final timestamp = DateTime.tryParse(item['timestamp'] ?? '');
    final timeStr = timestamp != null ? DateFormat('hh:mm a').format(timestamp) : '--:--';
    final dateStr = timestamp != null ? DateFormat('MMM dd, yyyy').format(timestamp) : 'Unknown Date';
    
    final severityText = (item['severity'] ?? 'low').toString().toLowerCase();
    Color severityColor = kSeverityLow;
    if (severityText == 'critical') severityColor = kSeverityCritical;
    else if (severityText == 'high') severityColor = kSeverityCritical; // Treat high as critical for UI
    else if (severityText == 'medium') severityColor = kSeverityMedium;

    return Container(
      margin: EdgeInsets.only(bottom: 16),
      padding: EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Colors.blueGrey[50]!),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.03),
            blurRadius: 10,
            offset: Offset(0, 4),
          )
        ],
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          // Thumbnail Image
          Container(
            width: 80,
            height: 80,
            decoration: BoxDecoration(
              color: Colors.blueGrey[100],
              borderRadius: BorderRadius.circular(12),
            ),
            child: ClipRRect(
              borderRadius: BorderRadius.circular(12),
              child: item['image_url'] != null
                  ? Image.network(
                      item['image_url'],
                      fit: BoxFit.cover,
                      errorBuilder: (context, _, __) => Icon(Icons.image_not_supported, color: Colors.blueGrey[300]),
                    )
                  : Icon(Icons.local_fire_department, color: Colors.blueGrey[300]),
            ),
          ),
          SizedBox(width: 16),
          
          // Details Column
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Container(
                      padding: EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                      decoration: BoxDecoration(
                        color: severityColor.withOpacity(0.1),
                        borderRadius: BorderRadius.circular(20),
                      ),
                      child: Text(
                        severityText.toUpperCase(),
                        style: TextStyle(
                          color: severityColor,
                          fontSize: 10,
                          fontWeight: FontWeight.bold,
                          letterSpacing: 0.5,
                        ),
                      ),
                    ),
                    Text(
                      timeStr,
                      style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: Colors.blueGrey[400]),
                    ),
                  ],
                ),
                SizedBox(height: 8),
                Text(
                  item['address'] ?? 'Unknown Location',
                  style: TextStyle(fontSize: 15, fontWeight: FontWeight.bold, color: kTextDark),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
                SizedBox(height: 2),
                Text(
                  dateStr,
                  style: TextStyle(fontSize: 13, fontWeight: FontWeight.w500, color: Colors.blueGrey[500]),
                ),
              ],
            ),
          ),
          
          Icon(Icons.chevron_right, color: Colors.blueGrey[300]),
        ],
      ),
    );
  }

  Widget _buildBottomNav(BuildContext context, Color activeColor) {
    return ClipRRect(
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: 12, sigmaY: 12),
        child: Container(
          padding: EdgeInsets.only(top: 16, bottom: 32, left: 24, right: 24),
          decoration: BoxDecoration(
            color: Colors.white.withOpacity(0.9),
            border: Border(top: BorderSide(color: Colors.blueGrey[100]!)),
          ),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              _buildNavItem(Icons.grid_view, 'DASHBOARD', false, () => Navigator.pushReplacementNamed(context, '/dashboard'), activeColor),
              _buildNavItem(Icons.map_outlined, 'EXPLORER', false, () {}, activeColor),
              
              _buildNavItem(Icons.history, 'HISTORY', true, () {}, activeColor),
              
              // Notifications item with red dot
              GestureDetector(
                onTap: () {},
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Stack(
                      clipBehavior: Clip.none,
                      children: [
                        Icon(Icons.notifications_outlined, color: Colors.blueGrey[400]),
                        Positioned(
                          top: -2,
                          right: -2,
                          child: Container(
                            width: 10,
                            height: 10,
                            decoration: BoxDecoration(
                              color: Colors.red[500],
                              shape: BoxShape.circle,
                              border: Border.all(color: Colors.white, width: 2),
                            ),
                          ),
                        ),
                      ],
                    ),
                    SizedBox(height: 4),
                    Text(
                      'ALERTS',
                      style: TextStyle(fontSize: 9, fontWeight: FontWeight.bold, color: Colors.blueGrey[400]),
                    ),
                  ],
                ),
              ),
              
              _buildNavItem(Icons.person_outline, 'PROFILE', false, () {}, activeColor),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildNavItem(IconData icon, String label, bool isActive, VoidCallback onTap, Color activeColor) {
    return GestureDetector(
      onTap: onTap,
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, color: isActive ? activeColor : Colors.blueGrey[400]),
          SizedBox(height: 4),
          Text(
            label,
            style: TextStyle(
              fontSize: 9,
              fontWeight: FontWeight.bold,
              color: isActive ? activeColor : Colors.blueGrey[400],
            ),
          ),
        ],
      ),
    );
  }
}
