import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'screens/login.dart';
import 'screens/dashboard_screen.dart';
import 'core/theme_manager.dart';
import 'screens/wallet_screen.dart';
import 'screens/history_screen.dart';
import 'package:provider/provider.dart';
import 'widgets/trading_view_chart.dart';
import 'widgets/order_book.dart';
import 'widgets/price_ticker.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';

// Gestión de estado global
class AppState extends ChangeNotifier {
  bool _isProMode = false;
  bool get isProMode => _isProMode;

  List<dynamic> _watchlist = [];
  List<dynamic> get watchlist => _watchlist;
  bool _isLoadingWatchlist = false;
  bool get isLoadingWatchlist => _isLoadingWatchlist;

  void toggleProMode() {
    _isProMode = !_isProMode;
    notifyListeners();
    _saveSettings();
  }

  Future<void> fetchWatchlist() async {
    final prefs = await SharedPreferences.getInstance();
    final token = prefs.getString('auth_token');
    if (token == null) return;

    _isLoadingWatchlist = true;
    notifyListeners();

    try {
      final response = await http.get(
        Uri.parse('http://127.0.0.1:8001/user/watchlist'),
        headers: {'Authorization': 'Bearer $token'},
      );
      if (response.statusCode == 200) {
        _watchlist = json.decode(response.body)['watchlist'] ?? [];
      }
    } catch (e) {
      debugPrint("Error fetching watchlist: $e");
    } finally {
      _isLoadingWatchlist = false;
      notifyListeners();
    }
  }

  Future<bool> toggleWatchlist(String ticker) async {
    final prefs = await SharedPreferences.getInstance();
    final token = prefs.getString('auth_token');
    if (token == null) return false;

    ticker = ticker.toUpperCase();
    final isFav = _watchlist.any((stock) => stock['ticker'] == ticker);

    // Optimistic update
    if (isFav) {
      _watchlist.removeWhere((stock) => stock['ticker'] == ticker);
    } else {
      _watchlist.add({'ticker': ticker, 'nombre': ticker});
    }
    notifyListeners();

    try {
      final response = isFav
          ? await http.delete(
              Uri.parse('http://127.0.0.1:8001/user/watchlist/$ticker'),
              headers: {'Authorization': 'Bearer $token'},
            )
          : await http.post(
              Uri.parse('http://127.0.0.1:8001/user/watchlist/$ticker'),
              headers: {'Authorization': 'Bearer $token'},
            );

      if (response.statusCode != 200) {
        await fetchWatchlist(); // Revert on server error
        return false;
      }
      return true;
    } catch (e) {
      await fetchWatchlist(); // Revert on network error
      return false;
    }
  }

  Future<void> loadSettings() async {
    final prefs = await SharedPreferences.getInstance();
    _isProMode = prefs.getBool('is_pro_mode') ?? false;
    notifyListeners();
  }

  Future<void> _saveSettings() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool('is_pro_mode', _isProMode);
  }
}

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // Inicialización de Firebase (Opcional si no hay config todavía)
  try {
    await Firebase.initializeApp();
    FirebaseMessaging messaging = FirebaseMessaging.instance;
    await messaging.requestPermission();
    FirebaseMessaging.onMessage.listen((RemoteMessage message) {
      debugPrint("Mensaje recibido: ${message.notification?.title}");
    });
  } catch (e) {
    debugPrint(
      "Firebase init error: $e. Asegúrate de agregar google-services.json.",
    );
  }

  final appState = AppState();
  await appState.loadSettings();

  final prefs = await SharedPreferences.getInstance();

  // Cargar tema guardado
  final String? savedTheme = prefs.getString('theme_mode');
  if (savedTheme == 'light') {
    themeNotifier.value = ThemeMode.light;
  } else {
    themeNotifier.value = ThemeMode.dark;
  }

  final email = prefs.getString('user_email');
  runApp(
    ChangeNotifierProvider(
      create: (_) => appState,
      child: MyApp(initialEmail: email),
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
            textTheme: GoogleFonts.poppinsTextTheme(
              ThemeData.light().textTheme,
            ),
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
          home: initialEmail != null
              ? const MainDashboard()
              : const LoginScreen(),
        );
      },
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
  String _selectedPeriod = '1mo';
  Map<String, dynamic>? data;

  @override
  void initState() {
    super.initState();
    _fetchData();
  }

  Future<void> _fetchData([String? period]) async {
    final p = period ?? _selectedPeriod;
    setState(() {
      isLoading = true;
      _selectedPeriod = p;
    });
    try {
      final response = await http.get(
        Uri.parse('http://127.0.0.1:8001/predict/${widget.ticker}?period=$p'),
      );
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
        iconTheme: IconThemeData(
          color: Theme.of(context).textTheme.bodyLarge?.color,
        ),
        title: Text(
          widget.ticker,
          style: TextStyle(color: Theme.of(context).textTheme.bodyLarge?.color),
        ),
        actions: [
          Consumer<AppState>(
            builder: (context, appState, _) {
              final isFav = appState.watchlist.any(
                (s) =>
                    s['ticker'].toString().toUpperCase() ==
                    widget.ticker.toUpperCase(),
              );
              return IconButton(
                icon: Icon(
                  isFav ? Icons.star : Icons.star_border,
                  color: isFav ? Colors.amber : Colors.grey,
                ),
                onPressed: () async {
                  final success = await appState.toggleWatchlist(widget.ticker);
                  if (!success && context.mounted) {
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(
                        content: Text('Error al actualizar favoritos'),
                        backgroundColor: Colors.red,
                      ),
                    );
                  }
                },
              );
            },
          ),
        ],
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
    final bool isPro = Provider.of<AppState>(context).isProMode;

    return SingleChildScrollView(
      padding: EdgeInsets.all(isPro ? 10 : 25),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _buildHeaderCard(isPro),
          if (isPro) ...[
            const SizedBox(height: 20),
            OrderBook(
              basePrice: (data!['precio'] ?? data!['price'] ?? 0.0).toDouble(),
            ),
          ],
          const SizedBox(height: 25),
          Text(
            "AI Analysis",
            style: GoogleFonts.poppins(
              fontSize: 18,
              fontWeight: FontWeight.bold,
              color: Colors.white,
            ),
          ),
          const SizedBox(height: 15),
          _buildAIRecommendationCard(),
          const SizedBox(height: 40),
          _buildDecisionButtons(),
        ],
      ),
    );
  }

  Widget _buildHeaderCard(bool isPro) {
    var priceValue = (data!['precio'] ?? data!['price'] ?? 0.0);
    double price = priceValue is String
        ? double.parse(priceValue)
        : (priceValue as num).toDouble();

    final List ohlcRaw = data!['ohlc'] is List ? data!['ohlc'] : [];
    final List<Candle> candles = [];

    for (var e in ohlcRaw) {
      try {
        candles.add(
          Candle(
            date: DateTime.parse(e['date']),
            high: (e['high'] as num).toDouble(),
            low: (e['low'] as num).toDouble(),
            open: (e['open'] as num).toDouble(),
            close: (e['close'] as num).toDouble(),
            volume: (e['volume'] as num).toDouble(),
          ),
        );
      } catch (err) {
        debugPrint("Error parsing candle: $err");
      }
    }

    // Ordenar por fecha y luego revertir para que el más reciente esté al final si es necesario,
    // pero Candlesticks lib suele esperar el más reciente en el índice 0.
    // La API devuelve orden cronológico, así que .reversed.toList() es correcto para que
    // el índice 0 sea el más reciente.
    final List<Candle> processedCandles = candles.reversed.toList();

    return Container(
      padding: EdgeInsets.all(isPro ? 10 : 25),
      decoration: BoxDecoration(
        color: Theme.of(context).cardColor,
        borderRadius: BorderRadius.circular(25),
      ),
      child: Column(
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                widget.ticker,
                style: GoogleFonts.poppins(
                  fontSize: isPro ? 24 : 35,
                  fontWeight: FontWeight.bold,
                  color: Colors.white,
                ),
              ),
              PriceTicker(
                price: price,
                fontSize: isPro ? 20 : 28,
                color: Colors.lightBlueAccent,
              ),
            ],
          ),
          const SizedBox(height: 15),
          // Selector de Intervalos
          _buildTimeframeSelector(),
          const SizedBox(height: 15),
          SizedBox(
            height: isPro ? 450 : 350,
            child: isPro
                ? TradingViewChart(ticker: widget.ticker)
                : processedCandles.length >= 2
                ? Theme(
                    data: ThemeData.dark(),
                    child: Candlesticks(
                      key: ValueKey("${widget.ticker}_$_selectedPeriod"),
                      candles: processedCandles,
                    ),
                  )
                : const Center(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(Icons.show_chart, size: 50, color: Colors.grey),
                        SizedBox(height: 10),
                        Text(
                          "Datos insuficientes para el gráfico",
                          style: TextStyle(color: Colors.grey),
                        ),
                      ],
                    ),
                  ),
          ),
        ],
      ),
    );
  }

  Widget _buildTimeframeSelector() {
    final periods = [
      {'label': '1D', 'value': '1d'},
      {'label': '5D', 'value': '5d'},
      {'label': '15D', 'value': '15d'},
      {'label': '1M', 'value': '1mo'},
      {'label': '6M', 'value': '6mo'},
      {'label': '1A', 'value': '1y'},
    ];

    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      child: Row(
        children: periods.map((p) {
          final isSelected = _selectedPeriod == p['value'];
          return Padding(
            padding: const EdgeInsets.only(right: 8.0),
            child: ChoiceChip(
              label: Text(
                p['label']!,
                style: GoogleFonts.poppins(
                  fontSize: 12,
                  color: isSelected ? Colors.white : Colors.grey,
                  fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
                ),
              ),
              selected: isSelected,
              onSelected: (selected) {
                if (selected) _fetchData(p['value']);
              },
              selectedColor: Colors.lightBlueAccent,
              backgroundColor: const Color(0xFF2A2A2A),
              checkmarkColor: Colors.white,
              padding: const EdgeInsets.symmetric(horizontal: 4),
            ),
          );
        }).toList(),
      ),
    );
  }

  Widget _buildAIRecommendationCard() {
    // Obtenemos la recomendación y la pasamos a minúsculas para comparar
    final String rawRec = (data!['recomendacion'] ?? 'esperar')
        .toString()
        .toLowerCase();

    // Tu lógica de Python devuelve "comprar" o "no_comprar"
    bool isBuy = rawRec.contains("comprar");

    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: isBuy
            ? const Color(0xFF1B5E20).withAlpha(51)
            : const Color(0xFFBF360C).withAlpha(51),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(
          color: isBuy
              ? Colors.greenAccent.withAlpha(77)
              : Colors.redAccent.withAlpha(77),
        ),
      ),
      child: Row(
        children: [
          Icon(
            Icons.auto_awesome,
            color: isBuy ? Colors.greenAccent : Colors.redAccent,
          ),
          const SizedBox(width: 15),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  "ANÁLISIS DE IA",
                  style: GoogleFonts.poppins(
                    fontSize: 12,
                    fontWeight: FontWeight.bold,
                    color: Colors.grey[400],
                  ),
                ),
                Text(
                  rawRec.toUpperCase(), // Mostrará "COMPRAR" o "NO_COMPRAR"
                  style: GoogleFonts.poppins(
                    fontWeight: FontWeight.bold,
                    fontSize: 18,
                    color: isBuy ? Colors.greenAccent : Colors.redAccent,
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
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(12),
              ),
            ),
            child: const Text("No comprar"),
          ),
        ),
        const SizedBox(width: 15),
        Expanded(
          child: ElevatedButton(
            onPressed: _showBuyDialog,
            style: ElevatedButton.styleFrom(
              backgroundColor: Colors.lightBlueAccent,
              foregroundColor: Colors.white,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(12),
              ),
            ),
            child: const Text("Comprar"),
          ),
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
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Decisión registrada: $decision'),
            backgroundColor: Colors.lightBlueAccent,
          ),
        );
      }
    } catch (e) {
      debugPrint("Error saving decision: $e");
    }
  }

  void _showBuyDialog() {
    final TextEditingController qtyController = TextEditingController(
      text: "1",
    );
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: Text('Comprar ${widget.ticker}'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              "Precio actual: \$${(data!['precio'] ?? 0.0).toStringAsFixed(2)}",
            ),
            const SizedBox(height: 15),
            TextField(
              controller: qtyController,
              keyboardType: TextInputType.number,
              decoration: const InputDecoration(
                labelText: "Cantidad de acciones",
              ),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancelar'),
          ),
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
        Uri.parse(
          'http://127.0.0.1:8001/trade/buy?ticker=${widget.ticker}&quantity=$quantity',
        ),
        headers: {'Authorization': 'Bearer $token'},
      );

      final resData = json.decode(response.body);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(resData['message']),
            backgroundColor: resData['status'] == 'success'
                ? Colors.green
                : Colors.red,
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
>>>>>>> 845813032f3d1dc9efb730fe3f519829e7065169
