import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'screens/login.dart';
import 'screens/dashboard_screen.dart';
import 'core/theme_manager.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final prefs = await SharedPreferences.getInstance();
  
  // Cargar tema guardado
  final String? savedTheme = prefs.getString('theme_mode');
  if (savedTheme == 'light') {
    themeNotifier.value = ThemeMode.light;
  } else {
    themeNotifier.value = ThemeMode.dark;
  }

  final email = prefs.getString('user_email');
  runApp(MyApp(initialEmail: email));
}

class MyApp extends StatelessWidget {
  final String? initialEmail;
  const MyApp({super.key, this.initialEmail});

  @override
  Widget build(BuildContext context) {
    return ValueListenableBuilder<ThemeMode>(
      valueListenable: themeNotifier,
      builder: (_, ThemeMode currentMode, __) {
        return MaterialApp(
          title: 'Acciones Inteligentes',
          debugShowCheckedModeBanner: false,
          themeMode: currentMode,
          // TEMA CLARO
          theme: ThemeData(
            brightness: Brightness.light,
            primaryColor: Colors.lightBlueAccent,
            scaffoldBackgroundColor: const Color(0xFFF5F7FA),
            cardColor: Colors.white,
            textTheme: GoogleFonts.poppinsTextTheme(ThemeData.light().textTheme),
            appBarTheme: const AppBarTheme(
              backgroundColor: Colors.white,
              foregroundColor: Colors.black87,
              elevation: 0,
            ),
            colorScheme: ColorScheme.fromSeed(
              seedColor: Colors.lightBlueAccent,
              brightness: Brightness.light,
              primary: Colors.lightBlueAccent,
            ),
          ),
          // TEMA OSCURO
          darkTheme: ThemeData(
            brightness: Brightness.dark,
            primaryColor: Colors.lightBlueAccent,
            scaffoldBackgroundColor: const Color(0xFF121212),
            cardColor: const Color(0xFF1E1E1E),
            textTheme: GoogleFonts.poppinsTextTheme(ThemeData.dark().textTheme),
            appBarTheme: const AppBarTheme(
              backgroundColor: Color(0xFF1E1E1E),
              foregroundColor: Colors.white,
              elevation: 0,
            ),
            colorScheme: ColorScheme.fromSeed(
              seedColor: Colors.lightBlueAccent,
              brightness: Brightness.dark,
              primary: Colors.lightBlueAccent,
            ),
          ),
          home: initialEmail != null ? const MainDashboard() : const LoginScreen(),
        );
      },
    );
  }
}

