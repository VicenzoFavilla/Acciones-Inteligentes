import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:provider/provider.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';

import 'screens/login.dart';
import 'screens/dashboard_screen.dart';
import 'core/theme_manager.dart';
import 'providers/app_state.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // Inicialización de Firebase (Opcional si no hay config todavía)
  try {
    if (kIsWeb) {
      debugPrint("Saltando Firebase init en Web por falta de FirebaseOptions.");
    } else {
      await Firebase.initializeApp();
      FirebaseMessaging messaging = FirebaseMessaging.instance;
      await messaging.requestPermission();
      FirebaseMessaging.onMessage.listen((RemoteMessage message) {
        debugPrint("Mensaje recibido: ${message.notification?.title}");
      });
    }
  } catch (e) {
    debugPrint(
      "Firebase init error: $e. Asegúrate de agregar google-services.json.",
    );
  }

  final prefs = await SharedPreferences.getInstance();
  final initialEmail = prefs.getString('user_email');

  // Cargar preferencia de tema guardada
  final themeModeStr = prefs.getString('theme_mode');
  if (themeModeStr == 'light') {
    themeNotifier.value = ThemeMode.light;
  } else {
    themeNotifier.value = ThemeMode.dark;
  }

  runApp(
    ChangeNotifierProvider(
      create: (context) => AppState()..loadSettings()..fetchWatchlist(),
      child: MyApp(initialEmail: initialEmail),
    ),
  );
}

class MyApp extends StatelessWidget {
  final String? initialEmail;
  const MyApp({super.key, this.initialEmail});

  @override
  Widget build(BuildContext context) {
    return ValueListenableBuilder<ThemeMode>(
      valueListenable: themeNotifier,
      builder: (context, currentThemeMode, child) {
        return MaterialApp(
          title: 'Acciones Inteligentes',
          debugShowCheckedModeBanner: false,
          themeMode: currentThemeMode,
          theme: ThemeData(
            primaryColor: Colors.blueAccent,
            scaffoldBackgroundColor: const Color(0xFFF5F7FA),
            cardColor: Colors.white,
            textTheme: GoogleFonts.poppinsTextTheme(ThemeData.light().textTheme),
            appBarTheme: const AppBarTheme(
              backgroundColor: Colors.white,
              foregroundColor: Colors.black87,
              elevation: 0,
            ),
            colorScheme: ColorScheme.fromSeed(
              seedColor: Colors.blueAccent,
              brightness: Brightness.light,
            ),
          ),
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
          home: initialEmail != null
              ? const MainDashboard()
              : const LoginScreen(),
        );
      },
    );
  }
}
