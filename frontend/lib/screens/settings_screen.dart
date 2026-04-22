import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../main.dart'; // Para acceder a themeNotifier y AppState
import 'package:provider/provider.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  bool _isDarkMode = themeNotifier.value == ThemeMode.dark;
  bool _notificationsEnabled = true;

  Future<void> _toggleTheme(bool isDark) async {
    setState(() {
      _isDarkMode = isDark;
    });
    
    // Actualizar el notificador global
    themeNotifier.value = isDark ? ThemeMode.dark : ThemeMode.light;
    
    // Guardar preferencia
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('theme_mode', isDark ? 'dark' : 'light');
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    
    return Scaffold(
      backgroundColor: theme.scaffoldBackgroundColor,
      appBar: AppBar(
        title: Text("Configuración", style: GoogleFonts.poppins()),
      ),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          _buildSectionHeader("Preferencias Visuales"),
          _buildSettingTile(
            icon: _isDarkMode ? Icons.dark_mode : Icons.light_mode,
            title: "Modo Oscuro",
            subtitle: _isDarkMode ? "Activado" : "Desactivado",
            trailing: Switch(
              value: _isDarkMode,
              activeColor: Colors.lightBlueAccent,
              onChanged: _toggleTheme,
            ),
          ),
          _buildSettingTile(
            icon: Icons.speed,
            title: "Modo Pro",
            subtitle: "Interfaz avanzada y gráficos TradingView",
            trailing: Consumer<AppState>(
              builder: (context, appState, child) => Switch(
                value: appState.isProMode,
                activeColor: Colors.orangeAccent,
                onChanged: (val) => appState.toggleProMode(),
              ),
            ),
          ),
          const SizedBox(height: 20),
          _buildSectionHeader("Notificaciones"),
          _buildSettingTile(
            icon: Icons.notifications_none,
            title: "Alertas de Mercado",
            subtitle: "Recibir avisos de variaciones",
            trailing: Switch(
              value: _notificationsEnabled,
              activeColor: Colors.lightBlueAccent,
              onChanged: (val) => setState(() => _notificationsEnabled = val),
            ),
          ),
          const SizedBox(height: 20),
          _buildSectionHeader("Cuenta"),
          _buildSettingTile(
            icon: Icons.language,
            title: "Idioma",
            subtitle: "Español",
            trailing: const Icon(Icons.chevron_right, color: Colors.grey),
            onTap: () {
              // Implementación futura
            },
          ),
        ],
      ),
    );
  }

  Widget _buildSectionHeader(String title) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 10),
      child: Text(
        title.toUpperCase(),
        style: GoogleFonts.poppins(
          fontSize: 12,
          fontWeight: FontWeight.bold,
          color: Colors.lightBlueAccent,
          letterSpacing: 1.2,
        ),
      ),
    );
  }

  Widget _buildSettingTile({
    required IconData icon,
    required String title,
    required String subtitle,
    required Widget trailing,
    VoidCallback? onTap,
  }) {
    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      decoration: BoxDecoration(
        color: Theme.of(context).cardColor,
        borderRadius: BorderRadius.circular(15),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withAlpha(13),
            blurRadius: 10,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: ListTile(
        onTap: onTap,
        contentPadding: const EdgeInsets.symmetric(horizontal: 20, vertical: 5),
        leading: Container(
          padding: const EdgeInsets.all(8),
          decoration: BoxDecoration(
            color: Colors.lightBlueAccent.withAlpha(26),
            borderRadius: BorderRadius.circular(10),
          ),
          child: Icon(icon, color: Colors.lightBlueAccent, size: 22),
        ),
        title: Text(title, style: GoogleFonts.poppins(fontWeight: FontWeight.w600, fontSize: 16)),
        subtitle: Text(subtitle, style: GoogleFonts.poppins(fontSize: 12, color: Colors.grey)),
        trailing: trailing,
      ),
    );
  }
}
