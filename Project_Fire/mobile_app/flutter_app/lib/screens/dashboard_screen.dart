import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../services/api_service.dart';

import '../providers/dashboard_provider.dart';

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
      appBar: AppBar(
        title: Text('Dashboard'),
        backgroundColor: Colors.red,
        actions: [
          IconButton(
            icon: Icon(Icons.refresh),
            onPressed: _loadData,
          ),
        ],
      ),
      body: Consumer<DashboardProvider>(
        builder: (context, provider, child) {
          if (provider.isLoading && provider.stats.isEmpty) {
            return Center(child: CircularProgressIndicator());
          }
          
          if (provider.errorMessage != null && provider.stats.isEmpty) {
            return Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Text(provider.errorMessage!, textAlign: TextAlign.center),
                  SizedBox(height: 16),
                  ElevatedButton(
                    onPressed: _loadData,
                    child: Text('Retry'),
                  ),
                ],
              ),
            );
          }

          return RefreshIndicator(
            onRefresh: _loadData,
            child: SingleChildScrollView(
              padding: EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  if (provider.errorMessage != null)
                    Container(
                      padding: EdgeInsets.all(8),
                      margin: EdgeInsets.only(bottom: 16),
                      color: Colors.red[100],
                      child: Row(
                        children: [
                          Icon(Icons.error, color: Colors.red),
                          SizedBox(width: 8),
                          Expanded(child: Text(provider.errorMessage!, style: TextStyle(color: Colors.red))),
                          IconButton(
                            icon: Icon(Icons.close, color: Colors.red),
                            onPressed: () => provider.clearError(),
                          ),
                        ],
                      ),
                    ),
                  // Stats cards
                  Text(
                    'Statistics',
                    style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
                  ),
                  SizedBox(height: 10),
                  GridView.count(
                    shrinkWrap: true,
                    physics: NeverScrollableScrollPhysics(),
                    crossAxisCount: 2,
                    childAspectRatio: 1.5,
                    crossAxisSpacing: 10,
                    mainAxisSpacing: 10,
                    children: [
                      _buildStatCard(
                        'Total Detections',
                        provider.stats['total_detections']?.toString() ?? '0',
                        Icons.fireplace,
                        Colors.red,
                      ),
                      _buildStatCard(
                        'Active Fires',
                        provider.stats['active_fires']?.toString() ?? '0',
                        Icons.warning,
                        Colors.orange,
                      ),
                      _buildStatCard(
                        'Today',
                        provider.stats['today_detections']?.toString() ?? '0',
                        Icons.today,
                        Colors.blue,
                      ),
                      _buildStatCard(
                        'Verified',
                        provider.stats['by_status']?['verified']?.toString() ?? '0',
                        Icons.verified,
                        Colors.green,
                      ),
                    ],
                  ),
                  
                  SizedBox(height: 20),
                  
                  // Severity breakdown
                  Text(
                    'By Severity',
                    style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
                  ),
                  SizedBox(height: 10),
                  _buildSeverityChart(provider.stats),
                  
                  SizedBox(height: 20),
                  
                  // Recent detections
                  Text(
                    'Recent Detections',
                    style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
                  ),
                  SizedBox(height: 10),
                  provider.recentDetections.isEmpty
                      ? Center(child: Text('No detections yet'))
                      : ListView.builder(
                          shrinkWrap: true,
                          physics: NeverScrollableScrollPhysics(),
                          itemCount: provider.recentDetections.length,
                          itemBuilder: (context, index) {
                            var detection = provider.recentDetections[index];
                            return _buildDetectionTile(detection);
                          },
                        ),
                ],
              ),
            ),
          );
        },
      ),
    );
  }

  Widget _buildStatCard(String label, String value, IconData icon, Color color) {
    return Card(
      elevation: 4,
      child: Padding(
        padding: EdgeInsets.all(12),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(icon, color: color, size: 30),
            SizedBox(height: 5),
            Text(
              value,
              style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
            ),
            Text(
              label,
              style: TextStyle(fontSize: 12, color: Colors.grey),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildSeverityChart(Map<String, dynamic> stats) {
    var bySeverity = stats['by_severity'] ?? {};
    
    return Card(
      elevation: 4,
      child: Padding(
        padding: EdgeInsets.all(16),
        child: Column(
          children: [
            _buildSeverityBar('Critical', bySeverity['critical'] ?? 0, Colors.red[900]!, stats),
            _buildSeverityBar('High', bySeverity['high'] ?? 0, Colors.red, stats),
            _buildSeverityBar('Medium', bySeverity['medium'] ?? 0, Colors.orange, stats),
            _buildSeverityBar('Low', bySeverity['low'] ?? 0, Colors.green, stats),
          ],
        ),
      ),
    );
  }

  Widget _buildSeverityBar(String label, int count, Color color, Map<String, dynamic> stats) {
    double percentage = stats['total_detections'] != null && stats['total_detections'] > 0
        ? count / stats['total_detections']
        : 0;
    
    return Padding(
      padding: EdgeInsets.symmetric(vertical: 4),
      child: Row(
        children: [
          SizedBox(width: 60, child: Text(label)),
          Expanded(
            child: Stack(
              children: [
                Container(
                  height: 20,
                  decoration: BoxDecoration(
                    color: Colors.grey[300],
                    borderRadius: BorderRadius.circular(10),
                  ),
                ),
                Container(
                  height: 20,
                  width: MediaQuery.of(context).size.width * 0.5 * percentage,
                  decoration: BoxDecoration(
                    color: color,
                    borderRadius: BorderRadius.circular(10),
                  ),
                ),
              ],
            ),
          ),
          SizedBox(width: 10),
          Text('$count'),
        ],
      ),
    );
  }

  Widget _buildDetectionTile(Map<String, dynamic> detection) {
    return Card(
      margin: EdgeInsets.symmetric(vertical: 4),
      child: ListTile(
        leading: CircleAvatar(
          backgroundColor: _getSeverityColor(detection['severity']),
          child: Icon(Icons.warning, color: Colors.white, size: 20),
        ),
        title: Text(detection['address'] ?? 'Unknown location'),
        subtitle: Text(
          '${detection['severity']?.toUpperCase() ?? 'UNKNOWN'} • '
          '${(detection['confidence'] * 100).toStringAsFixed(1)}% confidence',
        ),
        trailing: Text(
          _formatTime(detection['timestamp']),
          style: TextStyle(fontSize: 12, color: Colors.grey),
        ),
        onTap: () {
          // Show details
        },
      ),
    );
  }

  Color _getSeverityColor(String? severity) {
    switch (severity) {
      case 'critical': return Color(0xFF8B0000);
      case 'high': return Color(0xFFDC3545);
      case 'medium': return Color(0xFFFFC107);
      case 'low': return Color(0xFF28A745);
      default: return Colors.grey;
    }
  }

  String _formatTime(String? timestamp) {
    if (timestamp == null) return '';
    try {
      var time = DateTime.parse(timestamp);
      var now = DateTime.now();
      var difference = now.difference(time);
      
      if (difference.inHours < 24) {
        return '${difference.inHours}h ago';
      } else {
        return '${difference.inDays}d ago';
      }
    } catch (e) {
      return '';
    }
  }
}