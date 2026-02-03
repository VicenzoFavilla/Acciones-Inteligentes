import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';

class ProfileScreen extends StatefulWidget {
  const ProfileScreen({super.key});

  @override
  State<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends State<ProfileScreen> {
  String? _email;
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _fetchUserProfile();
  }

  Future<void> _fetchUserProfile() async {
    final prefs = await SharedPreferences.getInstance();
    final email = prefs.getString('user_email');
    
    if (email == null) {
      setState(() => _isLoading = false);
      return;
    }

    try {
      final response = await http.get(Uri.parse('http://127.0.0.1:8000/user/$email'));
      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        if (data['status'] == 'success') {
          setState(() {
            _email = data['user']['email'];
            _isLoading = false;
          });
        }
      }
    } catch (e) {
      setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF5F7FA),
      appBar: AppBar(
        title: Text("Mi Perfil", style: GoogleFonts.poppins(color: Colors.black87)),
        backgroundColor: Colors.white,
        elevation: 0,
        iconTheme: const IconThemeData(color: Colors.black87),
      ),
      body: _isLoading 
        ? const Center(child: CircularProgressIndicator())
        : Center(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                const Icon(Icons.account_circle, size: 100, color: Colors.blueAccent),
                const SizedBox(height: 20),
                Text(
                  "Perfil de Inversor",
                  style: GoogleFonts.poppins(fontSize: 24, fontWeight: FontWeight.bold),
                ),
                const SizedBox(height: 10),
                Text(
                  _email ?? "No se pudo cargar el email",
                  style: GoogleFonts.poppins(fontSize: 16, color: Colors.grey),
                ),
              ],
            ),
          ),
    );
  }
}
