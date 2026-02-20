import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';

class HistoryScreen extends StatefulWidget {
  const HistoryScreen({super.key});

  @override
  _HistoryScreenState createState() => _HistoryScreenState();
}

class _HistoryScreenState extends State<HistoryScreen> {
  List<dynamic> transactions = [];
  bool isLoading = true;
  String? token;

  @override
  void initState() {
    super.initState();
    _fetchHistoryData();
  }

  Future<void> _fetchHistoryData() async {
    final prefs = await SharedPreferences.getInstance();
    token = prefs.getString('auth_token');
    
    if (token == null) {
      if (mounted) setState(() => isLoading = false);
      return;
    }

    try {
      final response = await http.get(
        Uri.parse('http://127.0.0.1:8001/wallet/history'),
        headers: {'Authorization': 'Bearer $token'},
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        setState(() {
          transactions = data['transactions'] ?? [];
        });
      } else {
        debugPrint("Server error history: ${response.statusCode}");
      }
      if (mounted) setState(() => isLoading = false);
    } catch (e) {
      debugPrint("Error fetching history: $e");
      if (mounted) setState(() => isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF5F7FA),
      appBar: AppBar(
        title: Text("Historial de Operaciones", style: GoogleFonts.poppins(color: Colors.black, fontWeight: FontWeight.bold)),
        backgroundColor: Colors.transparent,
        elevation: 0,
        iconTheme: const IconThemeData(color: Colors.black),
      ),
      body: isLoading
          ? const Center(child: CircularProgressIndicator())
          : transactions.isEmpty
              ? const Center(child: Text("No has realizado operaciones aún."))
              : ListView.builder(
                  padding: const EdgeInsets.all(25),
                  itemCount: transactions.length,
                  itemBuilder: (context, index) {
                    final t = transactions[index];
                    final isBuy = t['type'] == 'buy';
                    return Container(
                      margin: const EdgeInsets.only(bottom: 15),
                      padding: const EdgeInsets.all(15),
                      decoration: BoxDecoration(
                        color: Colors.white,
                        borderRadius: BorderRadius.circular(20),
                        boxShadow: [BoxShadow(color: Colors.black.withOpacity(0.02), blurRadius: 10)],
                      ),
                      child: Row(
                        children: [
                          Icon(
                            isBuy ? Icons.arrow_downward : Icons.arrow_upward,
                            color: isBuy ? Colors.green : Colors.red,
                          ),
                          const SizedBox(width: 15),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text('${isBuy ? "Compra" : "Venta"} de ${t['ticker']}', 
                                  style: GoogleFonts.poppins(fontWeight: FontWeight.bold)),
                                Text('${t['quantity']} acciones a \$${t['price']}', 
                                  style: GoogleFonts.poppins(color: Colors.grey, fontSize: 13)),
                              ],
                            ),
                          ),
                          Text(
                            _formatDate(t['timestamp']),
                            style: GoogleFonts.poppins(color: Colors.black54, fontSize: 12),
                          ),
                        ],
                      ),
                    );
                  },
                ),
    );
  }

  String _formatDate(String isoString) {
    try {
      final date = DateTime.parse(isoString);
      return "${date.day}/${date.month} ${date.hour}:${date.minute.toString().padLeft(2, '0')}";
    } catch (e) {
      return isoString;
    }
  }
}
