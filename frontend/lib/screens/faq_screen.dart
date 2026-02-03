import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

class FAQScreen extends StatelessWidget {
  const FAQScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF5F7FA),
      appBar: AppBar(
        title: Text("Preguntas Frecuentes", style: GoogleFonts.poppins(color: Colors.black87)),
        backgroundColor: Colors.white,
        elevation: 0,
        iconTheme: const IconThemeData(color: Colors.black87),
      ),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          _buildFAQItem("¿Cómo funciona la IA?", "Nuestra IA analiza patrones históricos para predecir tendencias."),
          _buildFAQItem("¿Es 100% preciso?", "Ninguna predicción es 100% segura. Usa esta herramienta como apoyo."),
          _buildFAQItem("¿Cómo contacto soporte?", "Envíanos un correo a soporte@accionesinteligentes.com"),
        ],
      ),
    );
  }

  Widget _buildFAQItem(String question, String answer) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 20),
      child: ExpansionTile(
        title: Text(question, style: GoogleFonts.poppins(fontWeight: FontWeight.bold)),
        children: [
          Padding(
            padding: const EdgeInsets.all(16.0),
            child: Text(answer, style: GoogleFonts.poppins(color: Colors.black87)),
          ),
        ],
      ),
    );
  }
}
