import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'package:fl_chart/fl_chart.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:web_socket_channel/web_socket_channel.dart';
import '../config/api_config.dart';
import '../models/stock_model.dart';
import 'settings_screen.dart';
import 'login.dart';
import 'wallet_screen.dart';
import 'history_screen.dart';
import 'stock_detail_screen.dart';

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
  
  List<StockModel> popularStocks = [];
  bool isLoadingPopular = true;
  
  List<StockModel> marketList = [];
  bool isLoadingMarket = true;
  
  List<StockModel> watchlist = [];
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
      _channel = WebSocketChannel.connect(Uri.parse(ApiConfig.wsUrl));
      _channel!.stream.listen((message) {
        final decoded = json.decode(message);
        if (decoded['type'] == 'market_tick') {
          final List updates = decoded['data'];
          if (mounted) {
            setState(() {
              for (var update in updates) {
                for (var stock in popularStocks) {
                  if (stock.ticker == update['ticker']) stock.updateFromSocket(update);
                }
                for (var stock in marketList) {
                  if (stock.ticker == update['ticker']) stock.updateFromSocket(update);
                }
                for (var stock in watchlist) {
                  if (stock.ticker == update['ticker']) stock.updateFromSocket(update);
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
      final response = await http.get(ApiConfig.buildUri('/popular'));
      if (response.statusCode == 200) {
        if (mounted) {
          setState(() {
            popularStocks = (json.decode(response.body) as List).map((i) => StockModel.fromJson(i)).toList();
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
      final response = await http.get(ApiConfig.buildUri('/market'));
      if (response.statusCode == 200) {
        if (mounted) {
          setState(() {
            final data = json.decode(response.body);
            if (data is Map && data.containsKey('items')) {
              marketList = (data['items'] as List).map((i) => StockModel.fromJson(i)).toList();
            } else if (data is List) {
              marketList = data.map((i) => StockModel.fromJson(i)).toList();
            }
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
        ApiConfig.buildUri('/user/watchlist'),
        headers: {'Authorization': 'Bearer $token'},
      );
      if (response.statusCode == 200) {
        if (mounted) {
          setState(() {
            final rawList = json.decode(response.body)['watchlist'] as List? ?? [];
            watchlist = rawList.map((i) => StockModel.fromJson(i)).toList();
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
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Debes iniciar sesión'), backgroundColor: Colors.red));
      }
      return;
    }

    ticker = ticker.toUpperCase();
    final isFav = watchlist.any((stock) => stock.ticker == ticker);

    // Optimistic update: reflejamos el cambio en la UI inmediatamente
    setState(() {
      if (isFav) {
        watchlist.removeWhere((stock) => stock.ticker == ticker);
      } else {
        watchlist.add(StockModel(
          ticker: ticker, nombre: ticker, precio: 0.0,
          variacion: 0.0, colorGreen: true, volumen: 0.0,
          marketCap: 0.0, history: <double>[],
        ));
      }
    });

    try {
      final http.Response response;
      if (isFav) {
        response = await http.delete(
          ApiConfig.buildUri('/user/watchlist/$ticker'),
          headers: {'Authorization': 'Bearer $token'},
        );
      } else {
        response = await http.post(
          ApiConfig.buildUri('/user/watchlist/$ticker'),
          headers: {'Authorization': 'Bearer $token'},
        );
      }

      if (response.statusCode != 200) {
        // Error del servidor: revertimos el update optimista
        debugPrint('Error watchlist: ${response.statusCode} ${response.body}');
        await _fetchWatchlist();
      }
      // Si fue exitoso, NO re-fetchiamos: la UI ya está correcta con el update optimista.
      // El re-fetch es lento (llama a Yahoo Finance por ticker) y causaba el parpadeo.
    } catch (e) {
      // Error de red: revertimos el update optimista
      debugPrint('Error toggleWatchlist: $e');
      await _fetchWatchlist();
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
                Text("¿Qué acción analizamos hoy?", style: GoogleFonts.poppins(color: Theme.of(context).textTheme.bodyMedium?.color?.withValues(alpha: 0.7), fontSize: 16)),
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
        children: popularStocks.map((stock) => _buildPopularCard(stock)).toList(),
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
        boxShadow: [BoxShadow(color: Theme.of(context).brightness == Brightness.dark ? Colors.black.withValues(alpha: 0.2) : Colors.grey.withValues(alpha: 0.2), blurRadius: 15, offset: const Offset(0, 8))],
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
          ...watchlist.map((market) => _buildMarketRow(market)).toList(),
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
        boxShadow: [BoxShadow(color: Theme.of(context).brightness == Brightness.dark ? Colors.black.withValues(alpha: 0.2) : Colors.grey.withValues(alpha: 0.2), blurRadius: 15, offset: const Offset(0, 8))],
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
          ...marketList.map((market) => _buildMarketRow(market)).toList(),
        ],
      ),
    );
  }

  Widget _buildMarketRow(StockModel market) {
    final String ticker = market.ticker;
    final String name = market.nombre;
    final double price = market.precio;
    final double change = market.variacion;
    final bool isUp = market.colorGreen;
    final Color trendColor = isUp ? const Color(0xFF00C853) : const Color(0xFFFF3D00); // Verde y rojo brillantes
    final num volume = market.volumen;
    final num marketCap = market.marketCap;

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
                    watchlist.any((s) => s.ticker == ticker) ? Icons.star : Icons.star_border, 
                    color: watchlist.any((s) => s.ticker == ticker) ? Colors.lightBlueAccent : Theme.of(context).textTheme.bodySmall?.color, 
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

  Widget _buildPopularCard(StockModel stock) {
    final String ticker = stock.ticker;
    final double price = stock.precio;
    final double change = stock.variacion;
    final bool isUp = stock.colorGreen;
    final Color trendColor = isUp ? Colors.green : Colors.red;
    
    final List<FlSpot> spots = stock.history.asMap().entries.map((e) {
      return FlSpot(e.key.toDouble(), e.value);
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
          boxShadow: [BoxShadow(color: Theme.of(context).brightness == Brightness.dark ? Colors.black.withValues(alpha: 0.1) : Colors.grey.withValues(alpha: 0.1), blurRadius: 15, offset: const Offset(0, 8))],
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
           children: [
             Text(ticker, style: GoogleFonts.poppins(fontWeight: FontWeight.bold, fontSize: 22, color: Theme.of(context).textTheme.titleLarge?.color)),
             Text("\$${price.toStringAsFixed(2)}", style: GoogleFonts.poppins(fontSize: 18, color: Theme.of(context).textTheme.bodyMedium?.color)),
             const SizedBox(height: 15),
            
            // Gráfica con altura fija y validación de spots
            SizedBox(
              height: 60,
              child: spots.length >= 2 
                ? LineChart(
                    LineChartData(
                      gridData: FlGridData(show: false),
                      titlesData: FlTitlesData(show: false),
                      borderData: FlBorderData(show: false),
                      lineBarsData: [
                        LineChartBarData(
                          spots: spots,
                          isCurved: true,
                          color: trendColor,
                          barWidth: 3,
                          dotData: FlDotData(show: false),
                          belowBarData: BarAreaData(show: true, color: trendColor.withValues(alpha: 0.1)),
                        ),
                      ],
                    ),
                  )
                : const Center(child: Icon(Icons.show_chart, color: Colors.grey)),
            ),
            const SizedBox(height: 15),
            Text("${isUp ? '+' : ''}${change.toStringAsFixed(2)}%", style: GoogleFonts.poppins(color: trendColor, fontWeight: FontWeight.bold, fontSize: 14)),
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
        boxShadow: [BoxShadow(color: Colors.black.withValues(alpha: 0.2), blurRadius: 10)],
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

