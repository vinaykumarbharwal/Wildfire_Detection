import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../services/api_service.dart';
import 'package:intl/intl.dart';

class HistoryScreen extends StatefulWidget {
  @override
  _HistoryScreenState createState() => _HistoryScreenState();
}

class _HistoryScreenState extends State<HistoryScreen> {
  @override
  Widget build(BuildContext context) {
    final apiService = Provider.of<ApiService>(context);

    return Scaffold(
      appBar: AppBar(
        title: Text('Detection History'),
        actions: [
          IconButton(
            icon: Icon(Icons.refresh),
            onPressed: () => setState(() {}),
          ),
        ],
      ),
      body: FutureBuilder<List<dynamic>>(
        future: apiService.getDetections(limit: 20),
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return Center(child: CircularProgressIndicator());
          }
          
          if (snapshot.hasError || snapshot.data == null) {
            return Center(child: Text('Error loading history'));
          }

          final items = snapshot.data!;
          
          if (items.isEmpty) {
            return Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(Icons.history, size: 64, color: Colors.grey),
                  SizedBox(height: 16),
                  Text('No detections found', style: TextStyle(color: Colors.grey)),
                ],
              ),
            );
          }

          return ListView.builder(
            itemCount: items.length,
            itemBuilder: (context, index) {
              final item = items[index];
              final timestamp = DateTime.parse(item['timestamp']);
              final dateStr = DateFormat('MMM dd, yyyy - HH:mm').format(timestamp);
              
              return Card(
                margin: EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                child: ListTile(
                  leading: item['image_url'] != null
                      ? ClipRRect(
                          borderRadius: BorderRadius.circular(4),
                          child: Image.network(
                            item['image_url'],
                            width: 60,
                            height: 60,
                            fit: BoxFit.cover,
                            errorBuilder: (context, _, __) => Icon(Icons.image_not_supported),
                          ),
                        )
                      : CircleAvatar(child: Icon(Icons.local_fire_department)),
                  title: Text(item['address'] ?? 'Unknown Location'),
                  subtitle: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(dateStr),
                      Text(
                        'Severity: ${item['severity']?.toUpperCase() ?? 'N/A'}',
                        style: TextStyle(
                          color: _getSeverityColor(item['severity']),
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ],
                  ),
                  trailing: Icon(Icons.chevron_right),
                  onTap: () {
                    // Show detail or full image dialog
                    _showDetailDialog(context, item);
                  },
                ),
              );
            },
          );
        },
      ),
    );
  }

  Color _getSeverityColor(String? severity) {
    switch (severity?.toLowerCase()) {
      case 'critical':
        return Colors.red[900]!;
      case 'high':
        return Colors.red;
      case 'medium':
        return Colors.orange;
      case 'low':
        return Colors.green;
      default:
        return Colors.grey;
    }
  }

  void _showDetailDialog(BuildContext context, Map<String, dynamic> item) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: Text('Detection Details'),
        content: SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              if (item['image_url'] != null)
                Image.network(
                  item['image_url'],
                  width: double.infinity,
                  height: 200,
                  fit: BoxFit.cover,
                ),
              SizedBox(height: 16),
              Text('Location: ${item['address'] ?? 'Unknown'}'),
              Text('Confidence: ${(item['confidence'] * 100).toStringAsFixed(1)}%'),
              Text('Status: ${item['status']}'),
              Text('City: ${item['city'] ?? 'N/A'}'),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: Text('Close'),
          ),
        ],
      ),
    );
  }
}
