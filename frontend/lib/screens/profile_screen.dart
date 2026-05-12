import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import '../config/api_config.dart';

class ProfileScreen extends StatefulWidget {
  const ProfileScreen({super.key});

  @override
  State<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends State<ProfileScreen> {
  String? _email;
  String? _name;
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
      final response = await http.get(ApiConfig.buildUri('/user/$email'));
      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        if (data['status'] == 'success') {
          setState(() {
            _email = data['user']['email'];
            _name = data['user']['name']; // Ahora leemos el nombre también
            _isLoading = false;
          });
        }
      }
    } catch (e) {
      setState(() => _isLoading = false);
    }
  }

  Future<void> _updateProfile(String newName) async {
    final prefs = await SharedPreferences.getInstance();
    final token = prefs.getString('auth_token');
    
    try {
      final response = await http.put(
        ApiConfig.buildUri('/user/update'),
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer $token',
        },
        body: json.encode({'name': newName}),
      );

      final data = json.decode(response.body);
      if (response.statusCode == 200 && data['status'] == 'success') {
        setState(() {
          _name = newName;
        });
        if (mounted) ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text("Perfil actualizado")));
      } else {
        if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(data['message'] ?? "Error al actualizar")));
      }
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text("Error de conexión")));
    }
  }

  Future<void> _changePassword(String oldPass, String newPass) async {
    final prefs = await SharedPreferences.getInstance();
    final token = prefs.getString('auth_token');

    try {
      final response = await http.post(
        ApiConfig.buildUri('/user/change_password'),
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer $token',
        },
        body: json.encode({
          'email': _email,
          'old_password': oldPass,
          'new_password': newPass
        }),
      );

      final data = json.decode(response.body);
      if (response.statusCode == 200 && data['status'] == 'success') {
        if (mounted) {
          Navigator.pop(context); // Cerrar diálogo
          ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text("Contraseña actualizada")));
        }
      } else {
        if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(data['message'] ?? "Error al cambiar contraseña")));
      }
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text("Error de conexión")));
    }
  }

  void _showEditProfileDialog() {
    final TextEditingController nameController = TextEditingController(text: _name ?? "");
    showDialog(
      context: context, 
      builder: (ctx) => AlertDialog(
        title: Text("Editar Perfil", style: GoogleFonts.poppins(fontWeight: FontWeight.bold, fontSize: 18, color: Colors.black)),
        content: TextField(
          controller: nameController,
          decoration: const InputDecoration(labelText: "Nombre Completo"),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text("Cancelar")),
          ElevatedButton(
            onPressed: () {
              Navigator.pop(ctx);
              _updateProfile(nameController.text);
            }, 
            child: const Text("Guardar")
          ),
        ],
      )
    );
  }

  void _showChangePasswordDialog() {
    final TextEditingController oldPassController = TextEditingController();
    final TextEditingController newPassController = TextEditingController();
    
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text("Cambiar Contraseña", style: GoogleFonts.poppins(fontWeight: FontWeight.bold, fontSize: 18, color: Colors.black)),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: oldPassController,
              decoration: const InputDecoration(labelText: "Contraseña Actual"),
              obscureText: true,
            ),
            const SizedBox(height: 10),
            TextField(
              controller: newPassController,
              decoration: const InputDecoration(labelText: "Nueva Contraseña"),
              obscureText: true,
            ),
          ],
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text("Cancelar")),
          ElevatedButton(
            onPressed: () {
              if (oldPassController.text.isNotEmpty && newPassController.text.isNotEmpty) {
                _changePassword(oldPassController.text, newPassController.text);
              }
            }, 
            child: const Text("Cambiar")
          ),
        ],
      )
    );
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
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(20),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                   Container(
                    width: 120, height: 120,
                    decoration: BoxDecoration(
                      color: Colors.blueAccent.withOpacity(0.1),
                      shape: BoxShape.circle,
                    ),
                    child: const Icon(Icons.person, size: 80, color: Colors.blueAccent),
                  ),
                  const SizedBox(height: 20),
                  Text(
                    _name?.isNotEmpty == true ? _name! : "Sin Nombre",
                    style: GoogleFonts.poppins(fontSize: 24, fontWeight: FontWeight.bold),
                  ),
                  const SizedBox(height: 5),
                  Text(
                    _email ?? "No email",
                    style: GoogleFonts.poppins(fontSize: 16, color: Colors.grey),
                  ),
                  const SizedBox(height: 40),
                  
                  // Botón Editar Perfil
                  SizedBox(
                    width: double.infinity,
                    child: ElevatedButton.icon(
                      style: ElevatedButton.styleFrom(
                        padding: const EdgeInsets.symmetric(vertical: 15),
                        backgroundColor: Colors.blueAccent,
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10))
                      ),
                      onPressed: _showEditProfileDialog, 
                      icon: const Icon(Icons.edit, color: Colors.white), 
                      label: Text("Editar Perfil", style: GoogleFonts.poppins(fontSize: 16, color: Colors.white))
                    ),
                  ),
                  const SizedBox(height: 20),
                  
                  // Botón Cambiar Contraseña
                  SizedBox(
                    width: double.infinity,
                    child: OutlinedButton.icon(
                      style: OutlinedButton.styleFrom(
                        padding: const EdgeInsets.symmetric(vertical: 15),
                        side: BorderSide(color: Colors.grey.shade400),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10))
                      ),
                      onPressed: _showChangePasswordDialog, 
                      icon: const Icon(Icons.lock_outline, color: Colors.black87), 
                      label: Text("Cambiar Contraseña", style: GoogleFonts.poppins(fontSize: 16, color: Colors.black87))
                    ),
                  ),
                ],
              ),
            ),
          ),
    );
  }
}
