import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'package:fl_chart/fl_chart.dart';
import 'package:shared_preferences/shared_preferences.dart';

// Pantallas externas (Asegúrate de que los archivos existan)
import 'screens/profile_screen.dart';
import 'screens/settings_screen.dart';
import 'screens/premium_screen.dart';
import 'screens/faq_screen.dart';
import 'screens/login.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final prefs = await SharedPreferences.getInstance();
  final email = prefs.getString('user_email');
  runApp(MyApp(initialEmail: email));
}

class MyApp extends StatelessWidget {
  final String? initialEmail;
  const MyApp({super.key, this.initialEmail});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Market AI Solver',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        primaryColor: Colors.blueAccent,
        textTheme: GoogleFonts.poppinsTextTheme(),
      ),
      home: initialEmail != null ? const MainDashboard() : const LoginScreen(),
    );
  }
}

class MainDashboard extends StatefulWidget {
  const MainDashboard({super.key});

  @override
  _MainDashboardState createState() => _MainDashboardState();
}

class _MainDashboardState extends State<MainDashboard> {
  final GlobalKey<ScaffoldState> _scaffoldKey = GlobalKey<ScaffoldState>();
  final TextEditingController _tickerController = TextEditingController();
  String? _userEmail;
  
  List<dynamic> popularStocks = [];
  bool isLoadingPopular = true;

  @override
  void initState() {
    super.initState();
    _loadUserEmail();
    _fetchPopularStocks();
  }

  Future<void> _loadUserEmail() async {
    final prefs = await SharedPreferences.getInstance();
    setState(() => _userEmail = prefs.getString('user_email'));
  }

  Future<void> _fetchPopularStocks() async {
    try {
      final response = await http.get(Uri.parse('http://127.0.0.1:8000/popular'));
      if (response.statusCode == 200) {
        if (mounted) {
          setState(() {
            popularStocks = json.decode(response.body);
            isLoadingPopular = false;
          });
        }
      }
    } catch (e) {
      debugPrint("Error al conectar con la API: $e");
      if (mounted) setState(() => isLoadingPopular = false);
    }
  }

  Future<void> _logout() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('user_email');
    if (mounted) {
      Navigator.pushReplacement(context, MaterialPageRoute(builder: (context) => const LoginScreen()));
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      key: _scaffoldKey,
      backgroundColor: const Color(0xFFF5F7FA),
      drawer: _buildDrawer(),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 25.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const SizedBox(height: 30),
              _buildHeader(),
              const SizedBox(height: 10),
              Text("¿Qué acción analizamos hoy?", style: GoogleFonts.poppins(color: Colors.grey[600], fontSize: 16)),
              const SizedBox(height: 25),
              _buildSearchBar(),
              const SizedBox(height: 35),
              Text("Recomendaciones Populares", style: GoogleFonts.poppins(fontSize: 18, fontWeight: FontWeight.bold)),
              const SizedBox(height: 15),
              _buildPopularList(),
              const Spacer(),
              _buildFooter(),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildHeader() {
    return Row(
      children: [
        IconButton(
          icon: const Icon(Icons.menu, size: 30, color: Colors.black87),
          onPressed: () => _scaffoldKey.currentState?.openDrawer(),
        ),
        const SizedBox(width: 8),
        Text("Market AI Solver", style: GoogleFonts.poppins(fontSize: 24, fontWeight: FontWeight.bold)),
      ],
    );
  }

  Widget _buildPopularList() {
    if (isLoadingPopular) return const Center(child: CircularProgressIndicator());
    if (popularStocks.isEmpty) return const Text("No hay datos disponibles");

    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      child: Row(
        children: popularStocks.map((stock) => _buildPopularCard(Map<String, dynamic>.from(stock))).toList(),
      ),
    );
  }

  Widget _buildPopularCard(Map<String, dynamic> stock) {
    // PROTECCIÓN DE DATOS: Asegurar tipos correctos para evitar excepciones
    final String ticker = stock['ticker']?.toString() ?? 'N/A';
    final String price = (stock['precio'] ?? stock['price'] ?? '0.00').toString();
    final String change = (stock['variacion'] ?? stock['change'] ?? '0.00%').toString();
    final bool isUp = stock['color_green'] ?? (!change.contains('-'));
    final Color trendColor = isUp ? Colors.green : Colors.red;
    
    // Lista de historial procesada de forma segura
    final List historyRaw = stock['history'] is List ? stock['history'] : [];
    final List<FlSpot> spots = historyRaw.asMap().entries.map((e) {
      final double val = (e.value as num?)?.toDouble() ?? 0.0;
      return FlSpot(e.key.toDouble(), val);
    }).toList();

    return GestureDetector(
      onTap: () => _navigateToDetail(ticker),
      child: Container(
        width: 350,
        margin: const EdgeInsets.only(right: 15),
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(25),
          boxShadow: [BoxShadow(color: Colors.black.withOpacity(0.03), blurRadius: 15, offset: const Offset(0, 8))],
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(ticker, style: GoogleFonts.poppins(fontWeight: FontWeight.bold, fontSize: 22)),
            Text("\$${double.parse(price).toStringAsFixed(2)}", style: GoogleFonts.poppins(fontSize: 18, color: Colors.black54)),
            const SizedBox(height: 15),
            
            // Gráfica con altura fija y validación de spots
            SizedBox(
              height: 60,
              child: spots.length >= 2 
                ? LineChart(
                    LineChartData(
                      gridData: const FlGridData(show: false),
                      titlesData: const FlTitlesData(show: false),
                      borderData: FlBorderData(show: false),
                      lineBarsData: [
                        LineChartBarData(
                          spots: spots,
                          isCurved: true,
                          color: trendColor,
                          barWidth: 3,
                          dotData: const FlDotData(show: false),
                          belowBarData: BarAreaData(show: true, color: trendColor.withOpacity(0.1)),
                        ),
                      ],
                    ),
                  )
                : const Center(child: Icon(Icons.show_chart, color: Colors.grey)),
            ),
            const SizedBox(height: 15),
            Text(change, style: GoogleFonts.poppins(color: trendColor, fontWeight: FontWeight.bold, fontSize: 14)),
          ],
        ),
      ),
    );
  }

  Widget _buildSearchBar() {
    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(15),
        boxShadow: [BoxShadow(color: Colors.black.withOpacity(0.05), blurRadius: 10)],
      ),
      child: TextField(
        controller: _tickerController,
        decoration: const InputDecoration(
          hintText: "Buscar Ticker (ej: MSFT)",
          prefixIcon: Icon(Icons.search, color: Colors.blueAccent),
          border: InputBorder.none,
          contentPadding: EdgeInsets.symmetric(vertical: 15),
        ),
        onSubmitted: (value) => _navigateToDetail(value.toUpperCase()),
      ),
    );
  }

  void _navigateToDetail(String symbol) {
    if (symbol.isEmpty) return;
    Navigator.push(context, MaterialPageRoute(builder: (context) => StockDetailScreen(ticker: symbol)));
  }

  Widget _buildFooter() {
    return Padding(
      padding: const EdgeInsets.only(bottom: 20),
      child: Center(child: Text("Hecho por Vicenzo Favilla", style: GoogleFonts.poppins(fontSize: 12, color: Colors.grey))),
    );
  }

  Widget _buildDrawer() {
    return Drawer(
      child: Container(
        color: const Color(0xFFB0B0B0),
        child: Column(
          children: [
            const SizedBox(height: 60),
            _userEmail != null 
              ? Column(
                  children: [
                    const Icon(Icons.account_circle_outlined, size: 80, color: Colors.black87),
                    const SizedBox(height: 10),
                    Text(_userEmail!, style: GoogleFonts.poppins(fontSize: 16, color: Colors.black87)),
                  ],
                )
              : const CircularProgressIndicator(),
            const SizedBox(height: 40),
            ListTile(
              leading: const Icon(Icons.settings_outlined, color: Colors.black87),
              title: const Text('Configuración'),
              onTap: () => Navigator.push(context, MaterialPageRoute(builder: (context) => const SettingsScreen())),
            ),
            const Spacer(),
            ListTile(
              leading: const Icon(Icons.logout, color: Colors.redAccent),
              title: const Text('Cerrar Sesión', style: TextStyle(color: Colors.redAccent)),
              onTap: _logout,
            ),
            const SizedBox(height: 20),
          ],
        ),
      ),
    );
  }
}

class StockDetailScreen extends StatefulWidget {
  final String ticker;
  const StockDetailScreen({super.key, required this.ticker});

  @override
  _StockDetailScreenState createState() => _StockDetailScreenState();
}

class _StockDetailScreenState extends State<StockDetailScreen> {
  bool isLoading = true;
  Map<String, dynamic>? data;

  @override
  void initState() {
    super.initState();
    _fetchData();
  }

  Future<void> _fetchData() async {
    try {
      final response = await http.get(Uri.parse('http://127.0.0.1:8000/predict/${widget.ticker}'));
      if (response.statusCode == 200 && mounted) {
        setState(() {
          data = json.decode(response.body);
          isLoading = false;
        });
      }
    } catch (e) {
      if (mounted) setState(() => isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        backgroundColor: const Color(0xFFF5F7FA), 
        elevation: 0, 
        iconTheme: const IconThemeData(color: Colors.black),
        title: Text(widget.ticker, style: const TextStyle(color: Colors.black)),
      ),
      backgroundColor: const Color(0xFFF5F7FA),
      body: isLoading 
        ? const Center(child: CircularProgressIndicator())
        : data == null 
          ? const Center(child: Text("No se pudo cargar la información"))
          : _buildDetailContent(),
    );
  }

  Widget _buildDetailContent() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(25),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _buildHeaderCard(),
          const SizedBox(height: 25),
          Text("AI Analysis", style: GoogleFonts.poppins(fontSize: 18, fontWeight: FontWeight.bold)),
          const SizedBox(height: 15),
          _buildAIRecommendationCard(),
          const SizedBox(height: 40),
          _buildDecisionButtons(),
        ],
      ),
    );
  }

  Widget _buildHeaderCard() {
    final String price = (data!['precio'] ?? data!['price'] ?? '0.00').toString();
    final List historyRaw = data!['history'] is List ? data!['history'] : [];
    final List<FlSpot> spots = historyRaw.asMap().entries.map((e) {
      final double val = (e.value as num?)?.toDouble() ?? 0.0;
      return FlSpot(e.key.toDouble(), val);
    }).toList();

    return Container(
      padding: const EdgeInsets.all(25),
      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(25)),
      child: Column(
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(widget.ticker, style: GoogleFonts.poppins(fontSize: 35, fontWeight: FontWeight.bold)),
              Text("\$$price", style: GoogleFonts.poppins(fontSize: 28, color: Colors.blueAccent)),
            ],
          ),
          const SizedBox(height: 20),
          SizedBox(
            height: 180,
            child: spots.length >= 2
              ? LineChart(
                  LineChartData(
                    gridData: const FlGridData(show: false),
                    titlesData: const FlTitlesData(show: false),
                    borderData: FlBorderData(show: false),
                    lineBarsData: [
                      LineChartBarData(
                        spots: spots,
                        isCurved: true,
                        color: Colors.blueAccent,
                        barWidth: 4,
                        belowBarData: BarAreaData(show: true, color: Colors.blueAccent.withOpacity(0.1)),
                      ),
                    ],
                  ),
                )
              : const Center(child: Icon(Icons.show_chart, size: 50, color: Colors.grey)),
          ),
        ],
      ),
    );
  }

  Widget _buildAIRecommendationCard() {
  // Obtenemos la recomendación y la pasamos a minúsculas para comparar
  final String rawRec = (data!['recomendacion'] ?? 'esperar').toString().toLowerCase();
  
  // Tu lógica de Python devuelve "comprar" o "no_comprar"
  bool isBuy = rawRec.contains("comprar");

  return Container(
    padding: const EdgeInsets.all(20),
    decoration: BoxDecoration(
      color: isBuy ? const Color(0xFFE8F5E9) : Colors.orange[50],
      borderRadius: BorderRadius.circular(20),
      border: Border.all(color: isBuy ? Colors.green.withOpacity(0.3) : Colors.orange.withOpacity(0.3))
    ),
    child: Row(
      children: [
        Icon(Icons.auto_awesome, color: isBuy ? Colors.green : Colors.orange),
        const SizedBox(width: 15),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                "ANÁLISIS DE IA",
                style: GoogleFonts.poppins(fontSize: 12, fontWeight: FontWeight.bold, color: Colors.black54),
              ),
              Text(
                rawRec.toUpperCase(), // Mostrará "COMPRAR" o "NO_COMPRAR"
                style: GoogleFonts.poppins(
                  fontWeight: FontWeight.bold, 
                  fontSize: 18,
                  color: isBuy ? Colors.green[900] : Colors.orange[900]
                ),
              ),
            ],
          ),
        ),
      ],
    ),
  );
}

  Widget _buildDecisionButtons() {
    return Row(
      children: [
        Expanded(child: OutlinedButton(onPressed: () {}, child: const Text("No comprar"))),
        const SizedBox(width: 15),
        Expanded(child: ElevatedButton(onPressed: () {}, child: const Text("Comprar"))),
      ],
    );
  }
}