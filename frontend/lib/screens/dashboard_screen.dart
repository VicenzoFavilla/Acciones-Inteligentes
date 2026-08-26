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
  static const int _marketPageSize = 50;
  int _marketCurrentPage = 1;
  int _marketTotalItems = 0;
  int _marketTotalPages = 1;

  List<StockModel> watchlist = [];
  bool isLoadingWatchlist = true;

  double _totalEquity = 0.0;
  double _dailyPnl = 0.0;
  double _dailyPnlPct = 0.0;
  List<String> _portfolioTickers = [];
  bool _isLoadingPortfolio = true;

  List<Map<String, dynamic>> _opportunities = [];
  bool _isLoadingOpportunities = true;
  String _opportunitiesDisclaimer = '';
  List<String> _recentTickers = [];

  WebSocketChannel? _channel;

  @override
  void initState() {
    super.initState();
    _loadUserData();
    _fetchPopularStocks();
    _fetchMarketData();
    _fetchWatchlist();
    _fetchDashboardWallet();
    _fetchOpportunities();
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
                  if (stock.ticker == update['ticker'])
                    stock.updateFromSocket(update);
                }
                for (var stock in marketList) {
                  if (stock.ticker == update['ticker'])
                    stock.updateFromSocket(update);
                }
                for (var stock in watchlist) {
                  if (stock.ticker == update['ticker'])
                    stock.updateFromSocket(update);
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
      _recentTickers = prefs.getStringList('recent_tickers') ?? [];
    });
  }

  Future<void> _fetchDashboardWallet() async {
    final prefs = await SharedPreferences.getInstance();
    final token = prefs.getString('auth_token');
    if (token == null) {
      if (mounted) setState(() => _isLoadingPortfolio = false);
      return;
    }

    try {
      final response = await http.get(
        ApiConfig.buildUri('/wallet/info'),
        headers: {'Authorization': 'Bearer $token'},
      );
      if (response.statusCode == 200 && mounted) {
        final wallet = json.decode(response.body)['wallet'] as Map<String, dynamic>;
        final positions = wallet['portfolio_details'] as List? ?? [];
        setState(() {
          _totalEquity = (wallet['total_equity'] as num? ?? 0).toDouble();
          _dailyPnl = (wallet['daily_pnl'] as num? ?? 0).toDouble();
          _dailyPnlPct = (wallet['daily_pnl_pct'] as num? ?? 0).toDouble();
          _portfolioTickers = positions
              .map((position) => position['ticker'].toString())
              .where((ticker) => ticker.isNotEmpty)
              .toList();
          _isLoadingPortfolio = false;
        });
      } else if (mounted) {
        setState(() => _isLoadingPortfolio = false);
      }
    } catch (_) {
      if (mounted) setState(() => _isLoadingPortfolio = false);
    }
  }

  Future<void> _fetchOpportunities() async {
    try {
      final response = await http.get(ApiConfig.buildUri('/opportunities'));
      if (response.statusCode == 200 && mounted) {
        final payload = json.decode(response.body) as Map<String, dynamic>;
        setState(() {
          _opportunities = (payload['items'] as List? ?? [])
              .map((item) => Map<String, dynamic>.from(item as Map))
              .toList();
          _opportunitiesDisclaimer = payload['disclaimer']?.toString() ?? '';
          _isLoadingOpportunities = false;
        });
      } else if (mounted) {
        setState(() => _isLoadingOpportunities = false);
      }
    } catch (_) {
      if (mounted) setState(() => _isLoadingOpportunities = false);
    }
  }

  Future<void> _fetchPopularStocks() async {
    try {
      final response = await http.get(ApiConfig.buildUri('/popular'));
      if (response.statusCode == 200) {
        if (mounted) {
          setState(() {
            popularStocks = (json.decode(response.body) as List)
                .map((i) => StockModel.fromJson(i))
                .toList();
            isLoadingPopular = false;
          });
        }
      }
    } catch (e) {
      debugPrint("Error al conectar con la API: $e");
      if (mounted) setState(() => isLoadingPopular = false);
    }
  }

  Future<void> _fetchMarketData([int page = 1]) async {
    if (mounted) {
      setState(() => isLoadingMarket = true);
    }
    try {
      final response = await http.get(
        ApiConfig.buildUri('/market', {
          'page': page,
          'page_size': _marketPageSize,
        }),
      );
      if (response.statusCode == 200) {
        if (mounted) {
          setState(() {
            final data = json.decode(response.body);
            if (data is Map && data.containsKey('items')) {
              marketList = (data['items'] as List)
                  .map((i) => StockModel.fromJson(i))
                  .toList();
              _marketCurrentPage = (data['current_page'] as num?)?.toInt() ?? page;
              _marketTotalItems = (data['total_items'] as num?)?.toInt() ?? marketList.length;
              _marketTotalPages = (data['total_pages'] as num?)?.toInt() ?? 1;
            } else if (data is List) {
              marketList = data.map((i) => StockModel.fromJson(i)).toList();
              _marketCurrentPage = 1;
              _marketTotalItems = marketList.length;
              _marketTotalPages = 1;
            }
            isLoadingMarket = false;
          });
        }
      } else if (mounted) {
        setState(() => isLoadingMarket = false);
      }
    } catch (e) {
      debugPrint("Error al conectar con la API de mercado: $e");
      if (mounted) setState(() => isLoadingMarket = false);
    }
  }

  void _changeMarketPage(int page) {
    if (page < 1 || page > _marketTotalPages || page == _marketCurrentPage) {
      return;
    }
    _fetchMarketData(page);
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
            final rawList =
                json.decode(response.body)['watchlist'] as List? ?? [];
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
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Debes iniciar sesión'),
            backgroundColor: Colors.red,
          ),
        );
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
        watchlist.add(
          StockModel(
            ticker: ticker,
            nombre: ticker,
            precio: 0.0,
            variacion: 0.0,
            colorGreen: true,
            volumen: 0.0,
            marketCap: 0.0,
            history: <double>[],
          ),
        );
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
      Navigator.pushReplacement(
        context,
        MaterialPageRoute(builder: (context) => const LoginScreen()),
      );
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
                const SizedBox(height: 20),
                _buildPortfolioSummary(),
                const SizedBox(height: 10),
                Text(
                  "¿Qué acción analizamos hoy?",
                  style: GoogleFonts.poppins(
                    color: Theme.of(
                      context,
                    ).textTheme.bodyMedium?.color?.withValues(alpha: 0.7),
                    fontSize: 16,
                  ),
                ),
                const SizedBox(height: 25),
                _buildSearchBar(),
                const SizedBox(height: 35),
                const SizedBox(height: 35),
                _buildSectionTitle(Icons.bolt, 'Movimientos del día'),
                const SizedBox(height: 15),
                _buildDailyMovers(),
                const SizedBox(height: 35),
                _buildSectionTitle(Icons.auto_awesome, 'Oportunidades con IA'),
                const SizedBox(height: 15),
                _buildOpportunities(),
                const SizedBox(height: 35),
                _buildSectionTitle(Icons.explore_outlined, 'Seguir explorando'),
                const SizedBox(height: 15),
                _buildExploreList(),
                const SizedBox(height: 35),
                Row(
                  children: [
                    Icon(Icons.star, color: Colors.lightBlueAccent, size: 20),
                    const SizedBox(width: 8),
                    Text(
                      "Mis Favoritos",
                      style: GoogleFonts.poppins(
                        fontSize: 18,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 15),
                _buildWatchlistTable(),
                const SizedBox(height: 35),
                Row(
                  children: [
                    Icon(
                      Icons.trending_up,
                      color: Colors.lightBlueAccent,
                      size: 20,
                    ),
                    const SizedBox(width: 8),
                    Text(
                      "Mercado de Acciones",
                      style: GoogleFonts.poppins(
                        fontSize: 18,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
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
        Text(
          "Acciones Inteligentes",
          style: GoogleFonts.poppins(
            fontSize: 24,
            fontWeight: FontWeight.bold,
            color: Theme.of(context).textTheme.headlineMedium?.color,
          ),
        ),
      ],
    );
  }

  Widget _buildPopularList() {
    if (isLoadingPopular)
      return const Center(child: CircularProgressIndicator());
    if (popularStocks.isEmpty) return const Text("No hay datos disponibles");

    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      child: Row(
        children: popularStocks
            .map((stock) => _buildPopularCard(stock))
            .toList(),
      ),
    );
  }

  Widget _buildWatchlistTable() {
    if (isLoadingWatchlist)
      return const Center(
        child: Padding(
          padding: EdgeInsets.all(20),
          child: CircularProgressIndicator(),
        ),
      );
    if (watchlist.isEmpty)
      return Padding(
        padding: const EdgeInsets.only(left: 5),
        child: Text(
          "Aún no tienes favoritos. Toca la estrella para agregar uno.",
          style: GoogleFonts.poppins(
            color: Theme.of(context).textTheme.bodySmall?.color,
          ),
        ),
      );

    return Container(
      decoration: BoxDecoration(
        color: Theme.of(context).cardColor,
        borderRadius: BorderRadius.circular(25),
        boxShadow: [
          BoxShadow(
            color: Theme.of(context).brightness == Brightness.dark
                ? Colors.black.withValues(alpha: 0.2)
                : Colors.grey.withValues(alpha: 0.2),
            blurRadius: 15,
            offset: const Offset(0, 8),
          ),
        ],
      ),
      padding: const EdgeInsets.all(20),
      child: Column(
        children: [
          Row(
            children: [
              Expanded(
                flex: 3,
                child: Text(
                  "Nombre",
                  style: GoogleFonts.poppins(
                    color: Theme.of(context).textTheme.bodySmall?.color,
                    fontSize: 12,
                  ),
                ),
              ),
              Expanded(
                flex: 2,
                child: Text(
                  "Precio",
                  style: GoogleFonts.poppins(
                    color: Theme.of(context).textTheme.bodySmall?.color,
                    fontSize: 12,
                  ),
                ),
              ),
              Expanded(
                flex: 2,
                child: Text(
                  "24h Cambio",
                  style: GoogleFonts.poppins(
                    color: Theme.of(context).textTheme.bodySmall?.color,
                    fontSize: 12,
                  ),
                  textAlign: TextAlign.right,
                ),
              ),
              Expanded(
                flex: 2,
                child: Text(
                  "Volumen",
                  style: GoogleFonts.poppins(
                    color: Theme.of(context).textTheme.bodySmall?.color,
                    fontSize: 12,
                  ),
                  textAlign: TextAlign.right,
                ),
              ),
              Expanded(
                flex: 2,
                child: Text(
                  "Cap. mercado",
                  style: GoogleFonts.poppins(
                    color: Theme.of(context).textTheme.bodySmall?.color,
                    fontSize: 12,
                  ),
                  textAlign: TextAlign.right,
                ),
              ),
              Expanded(
                flex: 1,
                child: Text(
                  "Acciones",
                  style: GoogleFonts.poppins(
                    color: Theme.of(context).textTheme.bodySmall?.color,
                    fontSize: 12,
                  ),
                  textAlign: TextAlign.center,
                ),
              ),
            ],
          ),
          const SizedBox(height: 15),
          Divider(color: Theme.of(context).dividerColor, height: 1),
          const SizedBox(height: 10),
          ...watchlist.map((market) => _buildMarketRow(market)),
        ],
      ),
    );
  }

  Widget _buildMarketTable() {
    if (isLoadingMarket)
      return const Center(
        child: Padding(
          padding: EdgeInsets.all(20),
          child: CircularProgressIndicator(),
        ),
      );
    if (marketList.isEmpty) return const Text("No hay datos disponibles");

    return Container(
      decoration: BoxDecoration(
        color: Theme.of(context).cardColor,
        borderRadius: BorderRadius.circular(25),
        boxShadow: [
          BoxShadow(
            color: Theme.of(context).brightness == Brightness.dark
                ? Colors.black.withValues(alpha: 0.2)
                : Colors.grey.withValues(alpha: 0.2),
            blurRadius: 15,
            offset: const Offset(0, 8),
          ),
        ],
      ),
      padding: const EdgeInsets.all(20),
      child: Column(
        children: [
          // Header
          Row(
            children: [
              Expanded(
                flex: 3,
                child: Text(
                  "Nombre",
                  style: GoogleFonts.poppins(
                    color: Theme.of(context).textTheme.bodySmall?.color,
                    fontSize: 12,
                  ),
                ),
              ),
              Expanded(
                flex: 2,
                child: Text(
                  "Precio",
                  style: GoogleFonts.poppins(
                    color: Theme.of(context).textTheme.bodySmall?.color,
                    fontSize: 12,
                  ),
                ),
              ),
              Expanded(
                flex: 2,
                child: Text(
                  "24h Cambio",
                  style: GoogleFonts.poppins(
                    color: Theme.of(context).textTheme.bodySmall?.color,
                    fontSize: 12,
                  ),
                  textAlign: TextAlign.right,
                ),
              ),
              Expanded(
                flex: 2,
                child: Text(
                  "Volumen",
                  style: GoogleFonts.poppins(
                    color: Theme.of(context).textTheme.bodySmall?.color,
                    fontSize: 12,
                  ),
                  textAlign: TextAlign.right,
                ),
              ),
              Expanded(
                flex: 2,
                child: Text(
                  "Cap. mercado",
                  style: GoogleFonts.poppins(
                    color: Theme.of(context).textTheme.bodySmall?.color,
                    fontSize: 12,
                  ),
                  textAlign: TextAlign.right,
                ),
              ),
              Expanded(
                flex: 1,
                child: Text(
                  "Acciones",
                  style: GoogleFonts.poppins(
                    color: Theme.of(context).textTheme.bodySmall?.color,
                    fontSize: 12,
                  ),
                  textAlign: TextAlign.center,
                ),
              ),
            ],
          ),
          const SizedBox(height: 15),
          Divider(color: Theme.of(context).dividerColor, height: 1),
          const SizedBox(height: 10),
          // Filas
          ...marketList.map((market) => _buildMarketRow(market)),
          const SizedBox(height: 16),
          _buildMarketPagination(),
        ],
      ),
    );
  }

  Widget _buildSectionTitle(IconData icon, String title) {
    return Row(
      children: [
        Icon(icon, color: Colors.lightBlueAccent, size: 20),
        const SizedBox(width: 8),
        Text(title, style: GoogleFonts.poppins(fontSize: 18, fontWeight: FontWeight.bold)),
      ],
    );
  }

  Widget _buildPortfolioSummary() {
    if (_isLoadingPortfolio) {
      return const SizedBox(height: 112, child: Center(child: CircularProgressIndicator()));
    }
    final isUp = _dailyPnl >= 0;
    final trendColor = isUp ? const Color(0xFF00C853) : const Color(0xFFFF5252);
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        gradient: const LinearGradient(colors: [Color(0xFF102A43), Color(0xFF1E3A5F)]),
        borderRadius: BorderRadius.circular(20),
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text('Resumen de cartera', style: GoogleFonts.poppins(color: Colors.white70, fontSize: 13)),
        const SizedBox(height: 4),
        Text('\$${_totalEquity.toStringAsFixed(2)}',
            style: GoogleFonts.poppins(color: Colors.white, fontSize: 28, fontWeight: FontWeight.bold)),
        const SizedBox(height: 12),
        Row(children: [
          Icon(isUp ? Icons.arrow_upward : Icons.arrow_downward, color: trendColor, size: 17),
          const SizedBox(width: 4),
          Text('Hoy: ${isUp ? '+' : ''}\$${_dailyPnl.toStringAsFixed(2)} '
              '(${isUp ? '+' : ''}${_dailyPnlPct.toStringAsFixed(2)}%)',
            style: GoogleFonts.poppins(color: trendColor, fontWeight: FontWeight.w600)),
          const Spacer(),
          Text('${_portfolioTickers.length} posiciones', style: GoogleFonts.poppins(color: Colors.white70, fontSize: 12)),
        ]),
      ]),
    );
  }

  Widget _buildDailyMovers() {
    if (isLoadingMarket) return const Center(child: CircularProgressIndicator());
    if (marketList.isEmpty) return const Text('No hay movimientos disponibles');
    final stocks = List<StockModel>.from(marketList);
    final gainers = List<StockModel>.from(stocks)..sort((a, b) => b.variacion.compareTo(a.variacion));
    final losers = List<StockModel>.from(stocks)..sort((a, b) => a.variacion.compareTo(b.variacion));
    final volume = List<StockModel>.from(stocks)..sort((a, b) => b.volumen.compareTo(a.volumen));
    return Row(children: [
      Expanded(child: _buildMoverCard('Mayor suba', gainers.first, Colors.greenAccent)),
      const SizedBox(width: 10),
      Expanded(child: _buildMoverCard('Mayor baja', losers.first, Colors.redAccent)),
      const SizedBox(width: 10),
      Expanded(child: _buildMoverCard('Más volumen', volume.first, Colors.lightBlueAccent)),
    ]);
  }

  Widget _buildMoverCard(String label, StockModel stock, Color color) {
    return GestureDetector(
      onTap: () => _navigateToDetail(stock.ticker),
      child: Container(
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(color: Theme.of(context).cardColor, borderRadius: BorderRadius.circular(14)),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(label, style: GoogleFonts.poppins(fontSize: 11, color: Colors.grey)),
          const SizedBox(height: 8),
          Text(stock.ticker, style: GoogleFonts.poppins(fontWeight: FontWeight.bold)),
          const SizedBox(height: 3),
          Text(label == 'Más volumen' ? _formatNumber(stock.volumen) : '${stock.variacion >= 0 ? '+' : ''}${stock.variacion.toStringAsFixed(2)}%',
            style: GoogleFonts.poppins(color: color, fontWeight: FontWeight.w600, fontSize: 12)),
        ]),
      ),
    );
  }

  Widget _buildOpportunities() {
    if (_isLoadingOpportunities) return const Center(child: CircularProgressIndicator());
    if (_opportunities.isEmpty) return const Text('No se pudieron cargar las señales por el momento.');
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        child: Row(children: _opportunities.map(_buildOpportunityCard).toList()),
      ),
      const SizedBox(height: 8),
      if (_opportunitiesDisclaimer.isNotEmpty)
        Text(_opportunitiesDisclaimer, style: GoogleFonts.poppins(fontSize: 11, color: Colors.grey)),
    ]);
  }

  Widget _buildOpportunityCard(Map<String, dynamic> item) {
    final ticker = item['ticker']?.toString() ?? '';
    final signal = item['signal']?.toString() ?? 'HOLD';
    final confidence = ((item['confidence'] as num?) ?? 0).toDouble();
    final price = ((item['price'] as num?) ?? 0).toDouble();
    final change = ((item['change'] as num?) ?? 0).toDouble();
    final color = switch (signal) {
      'BUY' => Colors.greenAccent,
      'SELL' => Colors.redAccent,
      _ => Colors.orangeAccent,
    };
    final history = (item['history'] as List? ?? [])
        .whereType<num>()
        .toList();
    final spots = history.asMap().entries
        .map((entry) => FlSpot(entry.key.toDouble(), entry.value.toDouble()))
        .toList();

    return GestureDetector(
      onTap: () => _navigateToDetail(ticker),
      child: Container(
        width: 300,
        height: 246,
        margin: const EdgeInsets.only(right: 12),
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: Theme.of(context).cardColor,
          borderRadius: BorderRadius.circular(18),
          border: Border.all(color: color.withValues(alpha: 0.3)),
        ),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Expanded(child: Text(ticker, style: GoogleFonts.poppins(fontSize: 20, fontWeight: FontWeight.bold))),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4),
              decoration: BoxDecoration(color: color.withValues(alpha: 0.14), borderRadius: BorderRadius.circular(10)),
              child: Text(signal, style: GoogleFonts.poppins(color: color, fontSize: 11, fontWeight: FontWeight.bold)),
            ),
          ]),
          Text('\$${price.toStringAsFixed(2)} · ${change >= 0 ? '+' : ''}${change.toStringAsFixed(2)}%',
            style: GoogleFonts.poppins(fontSize: 12, color: change >= 0 ? Colors.greenAccent : Colors.redAccent)),
          const SizedBox(height: 10),
          SizedBox(
            height: 72,
            child: spots.length >= 2
                ? LineChart(LineChartData(
                    gridData: FlGridData(show: false), titlesData: FlTitlesData(show: false),
                    borderData: FlBorderData(show: false),
                    lineBarsData: [LineChartBarData(spots: spots, isCurved: true, color: color, barWidth: 2, dotData: FlDotData(show: false))],
                  ))
                : const Center(child: Icon(Icons.show_chart, color: Colors.grey)),
          ),
          const SizedBox(height: 8),
          Text('Confianza del modelo: ${(confidence * 100).toStringAsFixed(0)}%',
            style: GoogleFonts.poppins(fontSize: 12, color: color, fontWeight: FontWeight.w600)),
          const SizedBox(height: 4),
          Text(item['reason']?.toString() ?? '', maxLines: 2, overflow: TextOverflow.ellipsis,
            style: GoogleFonts.poppins(fontSize: 10, color: Colors.grey)),
        ]),
      ),
    );
  }

  Widget _buildExploreList() {
    final tickers = <String>{..._portfolioTickers, ...watchlist.map((stock) => stock.ticker), ..._recentTickers, ...popularStocks.map((stock) => stock.ticker)}.take(6).toList();
    if (tickers.isEmpty) return const Text('Buscá una acción para comenzar a explorar.');
    return Wrap(spacing: 8, runSpacing: 8, children: tickers.map((ticker) => ActionChip(
      label: Text(ticker), avatar: const Icon(Icons.show_chart, size: 16), onPressed: () => _navigateToDetail(ticker),
    )).toList());
  }

  Widget _buildMarketPagination() {
    final firstItem = _marketTotalItems == 0
        ? 0
        : ((_marketCurrentPage - 1) * _marketPageSize) + 1;
    final lastItem = ((_marketCurrentPage * _marketPageSize) > _marketTotalItems)
        ? _marketTotalItems
        : _marketCurrentPage * _marketPageSize;

    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(
          'Mostrando $firstItem–$lastItem de $_marketTotalItems acciones',
          style: GoogleFonts.poppins(
            fontSize: 12,
            color: Theme.of(context).textTheme.bodySmall?.color,
          ),
        ),
        Row(
          children: [
            IconButton(
              tooltip: '50 acciones anteriores',
              onPressed: isLoadingMarket || _marketCurrentPage <= 1
                  ? null
                  : () => _changeMarketPage(_marketCurrentPage - 1),
              icon: const Icon(Icons.chevron_left),
            ),
            Text(
              '$_marketCurrentPage / $_marketTotalPages',
              style: GoogleFonts.poppins(fontSize: 12),
            ),
            IconButton(
              tooltip: 'Siguientes 50 acciones',
              onPressed: isLoadingMarket || _marketCurrentPage >= _marketTotalPages
                  ? null
                  : () => _changeMarketPage(_marketCurrentPage + 1),
              icon: const Icon(Icons.chevron_right),
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildMarketRow(StockModel market) {
    final String ticker = market.ticker;
    final String name = market.nombre;
    final double price = market.precio;
    final double change = market.variacion;
    final bool isUp = market.colorGreen;
    final Color trendColor = isUp
        ? const Color(0xFF00C853)
        : const Color(0xFFFF3D00); // Verde y rojo brillantes
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
                    backgroundColor: Colors
                        .primaries[ticker.hashCode % Colors.primaries.length],
                    child: Text(
                      ticker[0],
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 12,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Row(
                      children: [
                        Text(
                          ticker,
                          style: GoogleFonts.poppins(
                            color: Theme.of(context).textTheme.bodyLarge?.color,
                            fontWeight: FontWeight.bold,
                            fontSize: 14,
                          ),
                        ),
                        const SizedBox(width: 5),
                        Expanded(
                          child: Text(
                            name,
                            style: GoogleFonts.poppins(
                              color: Colors.grey,
                              fontSize: 11,
                            ),
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
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
                  Text(
                    "\$${price.toStringAsFixed(price < 1 ? 4 : 2)}",
                    style: GoogleFonts.poppins(
                      color: Theme.of(context).textTheme.bodyLarge?.color,
                      fontWeight: FontWeight.bold,
                      fontSize: 13,
                    ),
                  ),
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
                  style: GoogleFonts.poppins(
                    color: trendColor,
                    fontWeight: FontWeight.bold,
                    fontSize: 13,
                  ),
                ),
              ),
            ),
            // Volumen
            Expanded(
              flex: 2,
              child: Text(
                _formatNumber(volume),
                style: GoogleFonts.poppins(
                  color: Theme.of(context).textTheme.bodySmall?.color,
                  fontSize: 13,
                ),
                textAlign: TextAlign.right,
              ),
            ),
            // Cap. Mercado
            Expanded(
              flex: 2,
              child: Text(
                _formatNumber(marketCap),
                style: GoogleFonts.poppins(
                  color: Theme.of(context).textTheme.bodySmall?.color,
                  fontSize: 13,
                ),
                textAlign: TextAlign.right,
              ),
            ),
            // Acciones
            Expanded(
              flex: 1,
              child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  GestureDetector(
                    onTap: () => _navigateToDetail(ticker),
                    child: const Icon(
                      Icons.analytics_outlined,
                      color: Colors.lightBlueAccent,
                      size: 18,
                    ),
                  ),
                  const SizedBox(width: 8),
                  GestureDetector(
                    onTap: () => _toggleWatchlist(ticker),
                    child: Icon(
                      watchlist.any((s) => s.ticker == ticker)
                          ? Icons.star
                          : Icons.star_border,
                      color: watchlist.any((s) => s.ticker == ticker)
                          ? Colors.lightBlueAccent
                          : Theme.of(context).textTheme.bodySmall?.color,
                      size: 18,
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
          boxShadow: [
            BoxShadow(
              color: Theme.of(context).brightness == Brightness.dark
                  ? Colors.black.withValues(alpha: 0.1)
                  : Colors.grey.withValues(alpha: 0.1),
              blurRadius: 15,
              offset: const Offset(0, 8),
            ),
          ],
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              ticker,
              style: GoogleFonts.poppins(
                fontWeight: FontWeight.bold,
                fontSize: 22,
                color: Theme.of(context).textTheme.titleLarge?.color,
              ),
            ),
            Text(
              "\$${price.toStringAsFixed(2)}",
              style: GoogleFonts.poppins(
                fontSize: 18,
                color: Theme.of(context).textTheme.bodyMedium?.color,
              ),
            ),
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
                            belowBarData: BarAreaData(
                              show: true,
                              color: trendColor.withValues(alpha: 0.1),
                            ),
                          ),
                        ],
                      ),
                    )
                  : const Center(
                      child: Icon(Icons.show_chart, color: Colors.grey),
                    ),
            ),
            const SizedBox(height: 15),
            Text(
              "${isUp ? '+' : ''}${change.toStringAsFixed(2)}%",
              style: GoogleFonts.poppins(
                color: trendColor,
                fontWeight: FontWeight.bold,
                fontSize: 14,
              ),
            ),
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
        boxShadow: [
          BoxShadow(color: Colors.black.withValues(alpha: 0.2), blurRadius: 10),
        ],
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
    final ticker = symbol.toUpperCase();
    _saveRecentTicker(ticker);
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (context) => StockDetailScreen(ticker: ticker),
      ),
    );
  }

  Future<void> _saveRecentTicker(String ticker) async {
    final prefs = await SharedPreferences.getInstance();
    final updated = [
      ticker,
      ..._recentTickers.where((item) => item != ticker),
    ].take(6).toList();
    await prefs.setStringList('recent_tickers', updated);
    if (mounted) setState(() => _recentTickers = updated);
  }

  Widget _buildFooter() {
    return Padding(
      padding: const EdgeInsets.only(bottom: 20),
      child: Center(
        child: Text(
          "Hecho por Vicenzo Favilla",
          style: GoogleFonts.poppins(fontSize: 12, color: Colors.grey),
        ),
      ),
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
                      const Icon(
                        Icons.account_circle_outlined,
                        size: 80,
                        color: Colors.lightBlueAccent,
                      ),
                      const SizedBox(height: 10),
                      if (_userName != null && _userName!.isNotEmpty)
                        Text(
                          _userName!,
                          style: GoogleFonts.poppins(
                            fontSize: 18,
                            fontWeight: FontWeight.bold,
                            color: Colors.white,
                          ),
                        ),
                      Text(
                        _userEmail!,
                        style: GoogleFonts.poppins(
                          fontSize: 14,
                          color: Colors.grey[400],
                        ),
                      ),
                    ],
                  )
                : const CircularProgressIndicator(),
            const SizedBox(height: 40),
            ListTile(
              leading: const Icon(
                Icons.settings_outlined,
                color: Colors.white70,
              ),
              title: const Text(
                'Configuración',
                style: TextStyle(color: Colors.white),
              ),
              onTap: () => Navigator.push(
                context,
                MaterialPageRoute(builder: (context) => const SettingsScreen()),
              ),
            ),
            ListTile(
              leading: const Icon(
                Icons.account_balance_wallet_outlined,
                color: Colors.white70,
              ),
              title: const Text(
                'Mi Billetera',
                style: TextStyle(color: Colors.white),
              ),
              onTap: () => Navigator.push(
                context,
                MaterialPageRoute(builder: (context) => const WalletScreen()),
              ),
            ),
            ListTile(
              leading: const Icon(Icons.history, color: Colors.white70),
              title: const Text(
                'Historial',
                style: TextStyle(color: Colors.white),
              ),
              onTap: () => Navigator.push(
                context,
                MaterialPageRoute(builder: (context) => const HistoryScreen()),
              ),
            ),
            const Spacer(),
            ListTile(
              leading: const Icon(Icons.logout, color: Colors.redAccent),
              title: const Text(
                'Cerrar Sesión',
                style: TextStyle(color: Colors.redAccent),
              ),
              onTap: _logout,
            ),
            const SizedBox(height: 20),
          ],
        ),
      ),
    );
  }
}
