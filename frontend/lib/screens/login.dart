import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import 'dart:convert';
import '../main.dart'; // Import to access MainDashboard

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final TextEditingController _emailController = TextEditingController();
  final TextEditingController _passwordController = TextEditingController();
  bool _isLogin = true;
  bool _isLoading = false;

  Future<void> _submit() async {
    final email = _emailController.text.trim();
    final password = _passwordController.text.trim();

    if (email.isEmpty || password.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text("Por favor, completa todos los campos")),
      );
      return;
    }

    setState(() => _isLoading = true);

    try {
      final endpoint = _isLogin ? "login" : "register";
      final url = Uri.parse('http://127.0.0.1:8000/$endpoint');
      
      final response = await http.post(
        url,
        headers: {"Content-Type": "application/json"},
        body: json.encode({
          "email": email,
          "password": password,
        }),
      );

      final data = json.decode(response.body);

      if (response.statusCode == 200) {
        if (data['status'] == 'success') {
          if (_isLogin) {
            // Guardar sesión
            final prefs = await SharedPreferences.getInstance();
            await prefs.setString('user_email', email);

             Navigator.pushReplacement(
              context,
              MaterialPageRoute(builder: (context) => const MainDashboard()),
            );
          } else {
             ScaffoldMessenger.of(context).showSnackBar(
               SnackBar(content: Text(data['message'] ?? "Registro exitoso. Inicia sesión.")),
             );
             setState(() => _isLogin = true); // Switch to login after register
          }
        } else {
           ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text(data['message'] ?? "Error desconocido"), backgroundColor: Colors.red),
          );
        }
      } else {
         ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text("Error del servidor: ${response.statusCode}"), backgroundColor: Colors.red),
        );
      }
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text("Error de conexión: $e"), backgroundColor: Colors.red),
      );
    } finally {
      setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF5F7FA),
      body: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.symmetric(horizontal: 30),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                _isLogin ? "Bienvenido de nuevo" : "Crear Cuenta",
                style: GoogleFonts.poppins(
                  fontSize: 32,
                  fontWeight: FontWeight.bold,
                  color: Colors.black87,
                ),
              ),
              const SizedBox(height: 10),
              Text(
                _isLogin 
                  ? "Ingresa tus credenciales para continuar" 
                  : "Regístrate para comenzar a invertir",
                style: GoogleFonts.poppins(
                  fontSize: 16,
                  color: Colors.grey[600],
                ),
              ),
              const SizedBox(height: 40),
              
              _buildTextField("Email", Icons.email_outlined, _emailController),
              const SizedBox(height: 20),
              _buildTextField("Contraseña", Icons.lock_outline, _passwordController, isPassword: true),
              
              const SizedBox(height: 40),
              
              SizedBox(
                width: double.infinity,
                height: 55,
                child: ElevatedButton(
                  onPressed: _isLoading ? null : _submit,
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Colors.blueAccent,
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(15)),
                    elevation: 5,
                  ),
                  child: _isLoading 
                    ? const CircularProgressIndicator(color: Colors.white)
                    : Text(
                        _isLogin ? "Iniciar Sesión" : "Registrarse",
                        style: GoogleFonts.poppins(
                          fontSize: 18,
                          fontWeight: FontWeight.bold,
                          color: Colors.white,
                        ),
                      ),
                ),
              ),
              
              const SizedBox(height: 20),
              
              Center(
                child: GestureDetector(
                  onTap: () {
                    setState(() {
                      _isLogin = !_isLogin;
                    });
                  },
                  child: RichText(
                    text: TextSpan(
                      text: _isLogin ? "¿No tienes cuenta? " : "¿Ya tienes cuenta? ",
                      style: GoogleFonts.poppins(color: Colors.grey[600]),
                      children: [
                        TextSpan(
                          text: _isLogin ? "Regístrate" : "Inicia Sesión",
                          style: GoogleFonts.poppins(
                            color: Colors.blueAccent,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildTextField(String hint, IconData icon, TextEditingController controller, {bool isPassword = false}) {
    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(15),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.05),
            blurRadius: 10,
            offset: const Offset(0, 5),
          ),
        ],
      ),
      child: TextField(
        controller: controller,
        obscureText: isPassword,
        decoration: InputDecoration(
          prefixIcon: Icon(icon, color: Colors.blueAccent),
          hintText: hint,
          hintStyle: GoogleFonts.poppins(color: Colors.grey[400]),
          border: InputBorder.none,
          contentPadding: const EdgeInsets.symmetric(horizontal: 20, vertical: 15),
        ),
      ),
    );
  }
}
