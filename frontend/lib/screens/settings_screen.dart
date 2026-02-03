import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

class SettingsScreen extends StatelessWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF5F7FA),
      appBar: AppBar(
        title: Text("Configuración", style: GoogleFonts.poppins(color: Colors.black87)),
        backgroundColor: Colors.white,
        elevation: 0,
        iconTheme: const IconThemeData(color: Colors.black87),
      ),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          ListTile(
            leading: const Icon(Icons.notifications_outlined),
            title: Text("Notificaciones", style: GoogleFonts.poppins()),
            trailing: Switch(value: true, onChanged: (val) {}),
          ),
          const Divider(),
          ListTile(
            leading: const Icon(Icons.dark_mode_outlined),
            title: Text("Modo Oscuro", style: GoogleFonts.poppins()),
            trailing: Switch(value: false, onChanged: (val) {}),
          ),
          const Divider(),
          ListTile(
            leading: const Icon(Icons.language_outlined),
            title: Text("Idioma", style: GoogleFonts.poppins()),
            trailing: const Icon(Icons.chevron_right),
          ),
        ],
      ),
    );
  }
}
