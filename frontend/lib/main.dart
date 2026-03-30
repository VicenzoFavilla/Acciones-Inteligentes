import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'package:fl_chart/fl_chart.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:candlesticks/candlesticks.dart';
import 'package:web_socket_channel/web_socket_channel.dart';

// Pantallas externas
import 'screens/settings_screen.dart';
import 'screens/login.dart';
import 'screens/wallet_screen.dart';
import 'screens/history_screen.dart';

// Notificador global para el tema
final ValueNotifier<ThemeMode> themeNotifier = ValueNotifier(ThemeMode.dark);

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

class MainDashboard extends StatefulWidget {
  const MainDashboard({super.key});

  @override
  _MainDashboardState createState() => _MainDashboardState();
}

class _MainDashboardState extends State<MainDashboard> {
  final GlobalKey<ScaffoldState> _scaffoldKey = GlobalKey<ScaffoldState>();
  final TextEditingController _tickerController = TextEditingController();
  String? _userEmail;
  String? _userName;
  
  List<dynamic> popularStocks = [];
  bool isLoadingPopular = true;
  
  List<dynamic> marketList = [];
  bool isLoadingMarket = true;
  
  List<dynamic> watchlist = [];
  bool isLoadingWatchlist = true;
  
  WebSocketChannel? _channel;

  @override
  void initState() {
    super.initState();
    _loadUserData();
    _fetchPopularStocks();
    _fetchMarketData();
    _fetchWatchlist();
    _connectWebSocket();
  }
  
  void _connectWebSocket() {
    try {
      _channel = WebSocketChannel.connect(Uri.parse('ws://127.0.0.1:8001/ws/market'));
      _channel!.stream.listen((message) {
        final decoded = json.decode(message);
        if (decoded['type'] == 'market_tick') {
          final List updates = decoded['data'];
          if (mounted) {
            setState(() {
              for (var update in updates) {
                for (var stock in popularStocks) {
                  if (stock['ticker'] == update['ticker']) {
                    stock['precio'] = update['precio'];
                    stock['variacion'] = update['variacion'];
                    stock['color_green'] = update['color_green'];
                  }
                }
                for (var stock in marketList) {
                  if (stock['ticker'] == update['ticker']) {
                    stock['precio'] = update['precio'];
                    stock['variacion'] = update['variacion'];
                    stock['color_green'] = update['color_green'];
                  }
                }
                for (var stock in watchlist) {
                  if (stock['ticker'] == update['ticker']) {
                    stock['precio'] = update['precio'];
                    stock['variacion'] = update['variacion'];
                    stock['color_green'] = update['color_green'];
                  }
                }
              }
            });
          }
        }
      }, onError: (e) => debugPrint("WS Error: $e"));
    } catch (e) {
      debugPrint("WS Connect Error: $e");
    }
  }

  @override
  void dispose() {
    _channel?.sink.close();
    _tickerController.dispose();
    super.dispose();
  }

  Future<void> _loadUserData() async {
    final prefs = await SharedPreferences.getInstance();
    setState(() {
      _userEmail = prefs.getString('user_email');
      _userName = prefs.getString('user_name');
    });
  }

  Future<void> _fetchPopularStocks() async {
    try {
      final response = await http.get(Uri.parse('http://127.0.0.1:8001/popular'));
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

  Future<void> _fetchMarketData() async {
    try {
      final response = await http.get(Uri.parse('http://127.0.0.1:8001/market'));
      if (response.statusCode == 200) {
        if (mounted) {
          setState(() {
            marketList = json.decode(response.body);
            isLoadingMarket = false;
          });
        }
      }
    } catch (e) {
      debugPrint("Error al conectar con la API de mercado: $e");
      if (mounted) setState(() => isLoadingMarket = false);
    }
  }

  Future<void> _fetchWatchlist() async {
    final prefs = await SharedPreferences.getInstance();
    final token = prefs.getString('auth_token');
    if (token == null) {
      if (mounted) setState(() => isLoadingWatchlist = false);
      return;
    }

    try {
      final response = await http.get(
        Uri.parse('http://127.0.0.1:8001/user/watchlist'),
        headers: {'Authorization': 'Bearer $token'},
      );
      if (response.statusCode == 200) {
        if (mounted) {
          setState(() {
            watchlist = json.decode(response.body)['watchlist'] ?? [];
            isLoadingWatchlist = false;
          });
        }
      } else {
        if (mounted) setState(() => isLoadingWatchlist = false);
      }
    } catch (e) {
      if (mounted) setState(() => isLoadingWatchlist = false);
    }
  }

  Future<void> _toggleWatchlist(String ticker) async {
    final prefs = await SharedPreferences.getInstance();
    final token = prefs.getString('auth_token');
    if (token == null) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Debes iniciar sesión'), backgroundColor: Colors.red));
      return;
    }

    final isFav = watchlist.any((stock) => stock['ticker'] == ticker);

    try {
      // Optimistic update
      setState(() {
        if (isFav) {
          watchlist.removeWhere((stock) => stock['ticker'] == ticker);
        } else {
          watchlist.add({'ticker': ticker, 'nombre': ticker});
        }
      });
      
      if (isFav) {
        await http.delete(
          Uri.parse('http://127.0.0.1:8001/user/watchlist/$ticker'),
          headers: {'Authorization': 'Bearer $token'},
        );
      } else {
        await http.post(
          Uri.parse('http://127.0.0.1:8001/user/watchlist/$ticker'),
          headers: {'Authorization': 'Bearer $token'},
        );
      }
      _fetchWatchlist();
    } catch (e) {
      _fetchWatchlist(); // Revert on error
    }
  }

  String _formatNumber(num? number) {
    if (number == null) return "0";
    if (number >= 1e12) return "\$${(number / 1e12).toStringAsFixed(2)}T";
    if (number >= 1e9) return "\$${(number / 1e9).toStringAsFixed(2)}B";
    if (number >= 1e6) return "\$${(number / 1e6).toStringAsFixed(2)}M";
    return "\$${number.toStringAsFixed(2)}";
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
      backgroundColor: Theme.of(context).scaffoldBackgroundColor,
      drawer: _buildDrawer(),
      body: SafeArea(
        child: SingleChildScrollView(
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 20.0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const SizedBox(height: 30),
                _buildHeader(),
                const SizedBox(height: 10),
                Text("¿Qué acción analizamos hoy?", style: GoogleFonts.poppins(color: Theme.of(context).textTheme.bodyMedium?.color?.withAlpha(179), fontSize: 16)),
                const SizedBox(height: 25),
                _buildSearchBar(),
                const SizedBox(height: 35),
                Text("Acciones Populares", style: GoogleFonts.poppins(fontSize: 18, fontWeight: FontWeight.bold, color: Colors.lightBlueAccent)),
                const SizedBox(height: 15),
                _buildPopularList(),
                const SizedBox(height: 35),
                Row(
                   children: [
                      Icon(Icons.star, color: Colors.lightBlueAccent, size: 20),
                      const SizedBox(width: 8),
                      Text("Mis Favoritos", style: GoogleFonts.poppins(fontSize: 18, fontWeight: FontWeight.bold)),
                   ],
                ),
                const SizedBox(height: 15),
                _buildWatchlistTable(),
                const SizedBox(height: 35),
                Row(
                   children: [
                      Icon(Icons.trending_up, color: Colors.lightBlueAccent, size: 20),
                      const SizedBox(width: 8),
                      Text("Mercado de Acciones", style: GoogleFonts.poppins(fontSize: 18, fontWeight: FontWeight.bold)),
                   ],
                ),
                const SizedBox(height: 15),
                _buildMarketTable(),
                const SizedBox(height: 30),
                _buildFooter(),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildHeader() {
    return Row(
      children: [
        IconButton(
          icon: const Icon(Icons.menu, size: 30, color: Colors.lightBlueAccent),
          onPressed: () => _scaffoldKey.currentState?.openDrawer(),
        ),
        const SizedBox(width: 8),
        Text("Acciones Inteligentes", style: GoogleFonts.poppins(fontSize: 24, fontWeight: FontWeight.bold, color: Theme.of(context).textTheme.headlineMedium?.color)),
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

  Widget _buildWatchlistTable() {
    if (isLoadingWatchlist) return const Center(child: Padding(padding: EdgeInsets.all(20), child: CircularProgressIndicator()));
    if (watchlist.isEmpty) return Padding(padding: const EdgeInsets.only(left: 5), child: Text("Aún no tienes favoritos. Toca la estrella para agregar uno.", style: GoogleFonts.poppins(color: Theme.of(context).textTheme.bodySmall?.color)));

    return Container(
      decoration: BoxDecoration(
        color: Theme.of(context).cardColor,
        borderRadius: BorderRadius.circular(25),
        boxShadow: [BoxShadow(color: Theme.of(context).brightness == Brightness.dark ? Colors.black.withAlpha(51) : Colors.grey.withAlpha(51), blurRadius: 15, offset: const Offset(0, 8))],
      ),
      padding: const EdgeInsets.all(20),
      child: Column(
        children: [
          Row(
            children: [
              Expanded(flex: 3, child: Text("Nombre", style: GoogleFonts.poppins(color: Theme.of(context).textTheme.bodySmall?.color, fontSize: 12))),
              Expanded(flex: 2, child: Text("Precio", style: GoogleFonts.poppins(color: Theme.of(context).textTheme.bodySmall?.color, fontSize: 12))),
              Expanded(flex: 2, child: Text("24h Cambio", style: GoogleFonts.poppins(color: Theme.of(context).textTheme.bodySmall?.color, fontSize: 12), textAlign: TextAlign.right)),
              Expanded(flex: 2, child: Text("Volumen", style: GoogleFonts.poppins(color: Theme.of(context).textTheme.bodySmall?.color, fontSize: 12), textAlign: TextAlign.right)),
              Expanded(flex: 2, child: Text("Cap. mercado", style: GoogleFonts.poppins(color: Theme.of(context).textTheme.bodySmall?.color, fontSize: 12), textAlign: TextAlign.right)),
              Expanded(flex: 1, child: Text("Acciones", style: GoogleFonts.poppins(color: Theme.of(context).textTheme.bodySmall?.color, fontSize: 12), textAlign: TextAlign.center)),
            ],
          ),
          const SizedBox(height: 15),
          Divider(color: Theme.of(context).dividerColor, height: 1),
          const SizedBox(height: 10),
          ...watchlist.map((market) => _buildMarketRow(Map<String, dynamic>.from(market))).toList(),
        ],
      ),
    );
  }

  Widget _buildMarketTable() {
    if (isLoadingMarket) return const Center(child: Padding(padding: EdgeInsets.all(20), child: CircularProgressIndicator()));
    if (marketList.isEmpty) return const Text("No hay datos disponibles");

    return Container(
      decoration: BoxDecoration(
        color: Theme.of(context).cardColor,
        borderRadius: BorderRadius.circular(25),
        boxShadow: [BoxShadow(color: Theme.of(context).brightness == Brightness.dark ? Colors.black.withAlpha(51) : Colors.grey.withAlpha(51), blurRadius: 15, offset: const Offset(0, 8))],
      ),
      padding: const EdgeInsets.all(20),
      child: Column(
        children: [
          // Header
          Row(
            children: [
              Expanded(flex: 3, child: Text("Nombre", style: GoogleFonts.poppins(color: Theme.of(context).textTheme.bodySmall?.color, fontSize: 12))),
              Expanded(flex: 2, child: Text("Precio", style: GoogleFonts.poppins(color: Theme.of(context).textTheme.bodySmall?.color, fontSize: 12))),
              Expanded(flex: 2, child: Text("24h Cambio", style: GoogleFonts.poppins(color: Theme.of(context).textTheme.bodySmall?.color, fontSize: 12), textAlign: TextAlign.right)),
              Expanded(flex: 2, child: Text("Volumen", style: GoogleFonts.poppins(color: Theme.of(context).textTheme.bodySmall?.color, fontSize: 12), textAlign: TextAlign.right)),
              Expanded(flex: 2, child: Text("Cap. mercado", style: GoogleFonts.poppins(color: Theme.of(context).textTheme.bodySmall?.color, fontSize: 12), textAlign: TextAlign.right)),
              Expanded(flex: 1, child: Text("Acciones", style: GoogleFonts.poppins(color: Theme.of(context).textTheme.bodySmall?.color, fontSize: 12), textAlign: TextAlign.center)),
            ],
          ),
          const SizedBox(height: 15),
          Divider(color: Theme.of(context).dividerColor, height: 1),
          const SizedBox(height: 10),
          // Filas
          ...marketList.map((market) => _buildMarketRow(Map<String, dynamic>.from(market))).toList(),
        ],
      ),
    );
  }

  Widget _buildMarketRow(Map<String, dynamic> market) {
    final String ticker = market['ticker']?.toString() ?? 'N/A';
    final String name = market['nombre']?.toString() ?? ticker;
    final double price = (market['precio'] as num?)?.toDouble() ?? 0.0;
    final double change = (market['variacion'] as num?)?.toDouble() ?? 0.0;
    final bool isUp = change >= 0;
    final Color trendColor = isUp ? const Color(0xFF00C853) : const Color(0xFFFF3D00); // Verde y rojo brillantes
    final num volume = market['volumen'] ?? 0;
    final num marketCap = market['market_cap'] ?? 0;

    return GestureDetector(
      onTap: () => _navigateToDetail(ticker),
      behavior: HitTestBehavior.opaque,
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 12.0),
      child: Row(
        children: [
          // Nombre y Ticker
          Expanded(
            flex: 3,
            child: Row(
              children: [
                CircleAvatar(
                  radius: 12,
                  backgroundColor: Colors.primaries[ticker.hashCode % Colors.primaries.length],
                  child: Text(ticker[0], style: const TextStyle(color: Colors.white, fontSize: 12, fontWeight: FontWeight.bold)),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Row(
                    children: [
                      Text(ticker, style: GoogleFonts.poppins(color: Theme.of(context).textTheme.bodyLarge?.color, fontWeight: FontWeight.bold, fontSize: 14)),
                      const SizedBox(width: 5),
                      Expanded(child: Text(name, style: GoogleFonts.poppins(color: Colors.grey, fontSize: 11), overflow: TextOverflow.ellipsis)),
                    ],
                  ),
                ),
              ],
            ),
          ),
          // Precio
          Expanded(
            flex: 2,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
               children: [
                 Text("\$${price.toStringAsFixed(price < 1 ? 4 : 2)}", style: GoogleFonts.poppins(color: Theme.of(context).textTheme.bodyLarge?.color, fontWeight: FontWeight.bold, fontSize: 13)),
               ],
            ),
          ),
          // Cambio
          Expanded(
            flex: 2,
            child: Container(
              alignment: Alignment.centerRight,
              child: Text(
                "${isUp ? '+' : ''}${change.toStringAsFixed(2)}%", 
                style: GoogleFonts.poppins(color: trendColor, fontWeight: FontWeight.bold, fontSize: 13),
              ),
            ),
          ),
          // Volumen
           Expanded(
             flex: 2,
             child: Text(_formatNumber(volume), style: GoogleFonts.poppins(color: Theme.of(context).textTheme.bodySmall?.color, fontSize: 13), textAlign: TextAlign.right),
           ),
           // Cap. Mercado
           Expanded(
             flex: 2,
             child: Text(_formatNumber(marketCap), style: GoogleFonts.poppins(color: Theme.of(context).textTheme.bodySmall?.color, fontSize: 13), textAlign: TextAlign.right),
           ),
          // Acciones
          Expanded(
            flex: 1,
            child: Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                GestureDetector(
                  onTap: () => _navigateToDetail(ticker),
                  child: const Icon(Icons.analytics_outlined, color: Colors.lightBlueAccent, size: 18),
                ),
                const SizedBox(width: 8),
                GestureDetector(
                  onTap: () => _toggleWatchlist(ticker),
                  child: Icon(
                    watchlist.any((s) => s['ticker'] == ticker) ? Icons.star : Icons.star_border, 
                    color: watchlist.any((s) => s['ticker'] == ticker) ? Colors.lightBlueAccent : Theme.of(context).textTheme.bodySmall?.color, 
                    size: 18
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
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
          color: Theme.of(context).cardColor,
          borderRadius: BorderRadius.circular(25),
          boxShadow: [BoxShadow(color: Theme.of(context).brightness == Brightness.dark ? Colors.black.withAlpha(26) : Colors.grey.withAlpha(26), blurRadius: 15, offset: const Offset(0, 8))],
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
           children: [
             Text(ticker, style: GoogleFonts.poppins(fontWeight: FontWeight.bold, fontSize: 22, color: Theme.of(context).textTheme.titleLarge?.color)),
             Text("\$${double.parse(price).toStringAsFixed(2)}", style: GoogleFonts.poppins(fontSize: 18, color: Theme.of(context).textTheme.bodyMedium?.color)),
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
                          belowBarData: BarAreaData(show: true, color: trendColor.withAlpha(26)),
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
        color: const Color(0xFF1E1E1E),
        borderRadius: BorderRadius.circular(15),
        boxShadow: [BoxShadow(color: Colors.black.withAlpha(51), blurRadius: 10)],
      ),
      child: TextField(
        controller: _tickerController,
        style: const TextStyle(color: Colors.white),
        decoration: InputDecoration(
          hintText: "Buscar Ticker (ej: MSFT)",
          hintStyle: GoogleFonts.poppins(color: Colors.grey[600]),
          prefixIcon: const Icon(Icons.search, color: Colors.lightBlueAccent),
          border: InputBorder.none,
          contentPadding: const EdgeInsets.symmetric(vertical: 15),
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
        color: Theme.of(context).cardColor,
        child: Column(
          children: [
            const SizedBox(height: 60),
            _userEmail != null 
              ? Column(
                  children: [
                    const Icon(Icons.account_circle_outlined, size: 80, color: Colors.lightBlueAccent),
                    const SizedBox(height: 10),
                    if (_userName != null && _userName!.isNotEmpty)
                      Text(_userName!, style: GoogleFonts.poppins(fontSize: 18, fontWeight: FontWeight.bold, color: Colors.white)),
                    Text(_userEmail!, style: GoogleFonts.poppins(fontSize: 14, color: Colors.grey[400])),
                  ],
                )
              : const CircularProgressIndicator(),
            const SizedBox(height: 40),
            ListTile(
              leading: const Icon(Icons.settings_outlined, color: Colors.white70),
              title: const Text('Configuración', style: TextStyle(color: Colors.white)),
              onTap: () => Navigator.push(context, MaterialPageRoute(builder: (context) => const SettingsScreen())),
            ),
            ListTile(
              leading: const Icon(Icons.account_balance_wallet_outlined, color: Colors.white70),
              title: const Text('Mi Billetera', style: TextStyle(color: Colors.white)),
              onTap: () => Navigator.push(context, MaterialPageRoute(builder: (context) => const WalletScreen())),
            ),
            ListTile(
              leading: const Icon(Icons.history, color: Colors.white70),
              title: const Text('Historial', style: TextStyle(color: Colors.white)),
              onTap: () => Navigator.push(context, MaterialPageRoute(builder: (context) => const HistoryScreen())),
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
      final response = await http.get(Uri.parse('http://127.0.0.1:8001/predict/${widget.ticker}'));
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
        backgroundColor: Theme.of(context).cardColor, 
        elevation: 0, 
        iconTheme: IconThemeData(color: Theme.of(context).textTheme.bodyLarge?.color),
        title: Text(widget.ticker, style: TextStyle(color: Theme.of(context).textTheme.bodyLarge?.color)),
      ),
      backgroundColor: Theme.of(context).scaffoldBackgroundColor,
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
          Text("AI Analysis", style: GoogleFonts.poppins(fontSize: 18, fontWeight: FontWeight.bold, color: Colors.white)),
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
    
    final List ohlcRaw = data!['ohlc'] is List ? data!['ohlc'] : [];
    final List<Candle> candles = ohlcRaw.map((e) {
      return Candle(
        date: DateTime.parse(e['date']),
        high: (e['high'] as num).toDouble(),
        low: (e['low'] as num).toDouble(),
        open: (e['open'] as num).toDouble(),
        close: (e['close'] as num).toDouble(),
        volume: (e['volume'] as num).toDouble()
      );
    }).toList().reversed.toList(); // Candlesticks lib necesita el más reciente primero

    return Container(
      padding: const EdgeInsets.all(25),
      decoration: BoxDecoration(color: Theme.of(context).cardColor, borderRadius: BorderRadius.circular(25)),
      child: Column(
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(widget.ticker, style: GoogleFonts.poppins(fontSize: 35, fontWeight: FontWeight.bold, color: Colors.white)),
              Text("\$${double.parse(price).toStringAsFixed(2)}", style: GoogleFonts.poppins(fontSize: 28, color: Colors.lightBlueAccent, fontWeight: FontWeight.bold)),
            ],
          ),
          const SizedBox(height: 20),
          SizedBox(
            height: 350,
            child: candles.isNotEmpty
              ? Theme(
                  data: ThemeData.dark(),
                  child: Candlesticks(
                    candles: candles,
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
      color: isBuy ? const Color(0xFF1B5E20).withAlpha(51) : const Color(0xFFBF360C).withAlpha(51),
      borderRadius: BorderRadius.circular(20),
      border: Border.all(color: isBuy ? Colors.greenAccent.withAlpha(77) : Colors.redAccent.withAlpha(77))
    ),
    child: Row(
      children: [
        Icon(Icons.auto_awesome, color: isBuy ? Colors.greenAccent : Colors.redAccent),
        const SizedBox(width: 15),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                "ANÁLISIS DE IA",
                style: GoogleFonts.poppins(fontSize: 12, fontWeight: FontWeight.bold, color: Colors.grey[400]),
              ),
              Text(
                rawRec.toUpperCase(), // Mostrará "COMPRAR" o "NO_COMPRAR"
                style: GoogleFonts.poppins(
                  fontWeight: FontWeight.bold, 
                  fontSize: 18,
                  color: isBuy ? Colors.greenAccent : Colors.redAccent
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
        Expanded(
          child: OutlinedButton(
            onPressed: () => _handleDecision("no compré"), 
            style: OutlinedButton.styleFrom(
              side: const BorderSide(color: Colors.white24),
              foregroundColor: Colors.white70,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
            ),
            child: const Text("No comprar")
          )
        ),
        const SizedBox(width: 15),
        Expanded(
          child: ElevatedButton(
            onPressed: _showBuyDialog, 
            style: ElevatedButton.styleFrom(
              backgroundColor: Colors.lightBlueAccent,
              foregroundColor: Colors.white,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
            ),
            child: const Text("Comprar")
          )
        ),
      ],
    );
  }

  Future<void> _handleDecision(String decision) async {
    try {
      await http.post(
        Uri.parse('http://127.0.0.1:8001/decision'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({'ticker': widget.ticker, 'decision': decision}),
      );
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Decisión registrada: $decision'), backgroundColor: Colors.lightBlueAccent));
      }
    } catch (e) {
      debugPrint("Error saving decision: $e");
    }
  }

  void _showBuyDialog() {
    final TextEditingController qtyController = TextEditingController(text: "1");
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: Text('Comprar ${widget.ticker}'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text("Precio actual: \$${(data!['precio'] ?? 0.0).toStringAsFixed(2)}"),
            const SizedBox(height: 15),
            TextField(
              controller: qtyController,
              keyboardType: TextInputType.number,
              decoration: const InputDecoration(labelText: "Cantidad de acciones"),
            ),
          ],
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context), child: const Text('Cancelar')),
          ElevatedButton(
            onPressed: () {
              final int? qty = int.tryParse(qtyController.text);
              if (qty != null && qty > 0) {
                _executeTrade(qty);
                Navigator.pop(context);
              }
            },
            child: const Text('Comprar ahora'),
          ),
        ],
      ),
    );
  }

  Future<void> _executeTrade(int quantity) async {
    final prefs = await SharedPreferences.getInstance();
    final token = prefs.getString('auth_token');
    
    if (token == null) return;

    try {
      final response = await http.post(
        Uri.parse('http://127.0.0.1:8001/trade/buy?ticker=${widget.ticker}&quantity=$quantity'),
        headers: {'Authorization': 'Bearer $token'},
      );

      final resData = json.decode(response.body);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(resData['message']),
            backgroundColor: resData['status'] == 'success' ? Colors.green : Colors.red,
          ),
        );
        if (resData['status'] == 'success') {
          _handleDecision("compré");
        }
      }
    } catch (e) {
      debugPrint("Error executing trade: $e");
    }
  }
}