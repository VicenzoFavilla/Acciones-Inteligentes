import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
// Importamos fl_chart para las gráficas
import 'package:fl_chart/fl_chart.dart';

void main() {
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Acciones Inteligentes',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        primarySwatch: Colors.blue,
        textTheme: GoogleFonts.poppinsTextTheme(),
      ),
      home: const MainDashboard(),
    );
  }
}

// --- PANTALLA PRINCIPAL ---
class MainDashboard extends StatefulWidget {
  const MainDashboard({super.key});

  @override
  _MainDashboardState createState() => _MainDashboardState();
}

class _MainDashboardState extends State<MainDashboard> {
  final TextEditingController _tickerController = TextEditingController();

  // Lista de populares con datos de ejemplo para la gráfica (7 puntos de precio)
  final List<Map<String, dynamic>> popularStocks = [
    {
      'ticker': 'AAPL', 
      'price': 185.92, 
      'change': '+1.25%', 
      'color': Colors.green,
      'history': [180.0, 182.0, 181.5, 184.0, 183.0, 185.0, 185.92]
    },
    {
      'ticker': 'TSLA', 
      'price': 238.45, 
      'change': '-0.50%', 
      'color': Colors.red,
      'history': [245.0, 242.0, 240.0, 242.0, 239.0, 240.0, 238.45]
    },
    {
      'ticker': 'NVDA', 
      'price': 495.22, 
      'change': '+2.80%', 
      'color': Colors.green,
      'history': [470.0, 475.0, 480.0, 478.0, 485.0, 490.0, 495.22]
    },
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF5F7FA),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 25.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const SizedBox(height: 30),
              Text(
                "Acciones Inteligentes",
                style: GoogleFonts.poppins(fontSize: 28, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 10),
              Text(
                "¿Qué acción analizamos hoy?",
                style: GoogleFonts.poppins(color: Colors.grey[600], fontSize: 16),
              ),
              const SizedBox(height: 25),
              _buildSearchBar(),
              const SizedBox(height: 35),
              
              Text(
                "Recomendaciones Populares",
                style: GoogleFonts.poppins(fontSize: 18, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 15),
              
              // Lista Horizontal de Tarjetas GIGANTES con gráficas
              SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                child: Row(
                  children: popularStocks.map((stock) => _buildPopularCard(stock)).toList(),
                ),
              ),
              
              const Spacer(),
              Center(
                child: Text(
                  "Hecho por Vicenzo Favilla",
                  style: GoogleFonts.poppins(fontSize: 12, color: Colors.grey),
                ),
              ),
              const SizedBox(height: 20),
            ],
          ),
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
        decoration: InputDecoration(
          hintText: "Buscar Ticker (ej: MSFT)",
          prefixIcon: const Icon(Icons.search, color: Colors.blueAccent),
          border: InputBorder.none,
          contentPadding: const EdgeInsets.symmetric(vertical: 15),
        ),
        onSubmitted: (value) => _navigateToDetail(value.toUpperCase()),
      ),
    );
  }

  // --- WIDGET DE LA TARJETA POPULAR ---
  Widget _buildPopularCard(Map<String, dynamic> stock) {
    return GestureDetector(
      onTap: () => _navigateToDetail(stock['ticker']),
      child: Container(
        width: 600, // Aumentado para que sea más grande y quepa la gráfica
        margin: const EdgeInsets.only(right: 15),
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(25), // Bordes más redondeados
          boxShadow: [
            BoxShadow(color: Colors.black.withOpacity(0.03), blurRadius: 15, offset: const Offset(0, 8))
          ],
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(stock['ticker'], style: GoogleFonts.poppins(fontWeight: FontWeight.bold, fontSize: 22)),
            Text("\$${stock['price']}", style: GoogleFonts.poppins(fontSize: 18, color: Colors.black54)),
            
            const SizedBox(height: 15),
            
            // --- PEQUEÑA GRÁFICA (Sparkline) ---
            SizedBox(
              height: 60,
              child: LineChart(
                LineChartData(
                  gridData: const FlGridData(show: false),
                  titlesData: const FlTitlesData(show: false),
                  borderData: FlBorderData(show: false),
                  lineBarsData: [
                    LineChartBarData(
                      spots: (stock['history'] as List<double>).asMap().entries.map((e) {
                        return FlSpot(e.key.toDouble(), e.value);
                      }).toList(),
                      isCurved: true,
                      color: stock['color'],
                      barWidth: 3,
                      dotData: const FlDotData(show: false),
                      belowBarData: BarAreaData(
                        show: true,
                        color: (stock['color'] as Color).withOpacity(0.1),
                      ),
                    ),
                  ],
                ),
              ),
            ),
            
            const SizedBox(height: 15),
            
            Text(
              stock['change'],
              style: GoogleFonts.poppins(
                color: stock['color'], 
                fontWeight: FontWeight.bold, 
                fontSize: 14
              ),
            ),
          ],
        ),
      ),
    );
  }

  void _navigateToDetail(String symbol) {
    if (symbol.isEmpty) return;
    Navigator.push(
      context,
      MaterialPageRoute(builder: (context) => StockDetailScreen(ticker: symbol)),
    );
  }
}

// --- PANTALLA DE DETALLE ---
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
      // Conexión a tu backend FastAPI
      final response = await http.get(Uri.parse('http://127.0.0.1:8000/predict/${widget.ticker}'));
      if (response.statusCode == 200) {
        setState(() {
          data = json.decode(response.body);
          isLoading = false;
        });
      }
    } catch (e) {
      setState(() => isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        backgroundColor: const Color(0xFFF5F7FA), 
        elevation: 0, 
        iconTheme: const IconThemeData(color: Colors.black)
      ),
      backgroundColor: const Color(0xFFF5F7FA),
      body: isLoading 
        ? const Center(child: CircularProgressIndicator())
        : data == null 
          ? const Center(child: Text("No se encontró el ticker o el servidor está caído"))
          : SingleChildScrollView(
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
                  // Botones para alimentar tu MongoDB con 'decision_usuario'
                  _buildDecisionButtons(),
                ],
              ),
            ),
    );
  }

  Widget _buildHeaderCard() {
    return Container(
      padding: const EdgeInsets.all(25),
      decoration: BoxDecoration(
        color: Colors.white, 
        borderRadius: BorderRadius.circular(25),
        boxShadow: [BoxShadow(color: Colors.black.withOpacity(0.02), blurRadius: 20)]
      ),
      child: Column(
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(widget.ticker, style: GoogleFonts.poppins(fontSize: 35, fontWeight: FontWeight.bold)),
              Text(
                "\$${data!['precio'] ?? 'N/A'}", 
                style: GoogleFonts.poppins(fontSize: 28, color: Colors.blueAccent, fontWeight: FontWeight.bold)
              ),
            ],
          ),
          const SizedBox(height: 20),
          // Gráfica de precios real
          Container(
            height: 180,
            decoration: BoxDecoration(
              color: Colors.blue.withOpacity(0.02),
              borderRadius: BorderRadius.circular(20)
            ),
            child: (data!['history'] != null && (data!['history'] as List).isNotEmpty)
              ? Padding(
                  padding: const EdgeInsets.only(top: 20, right: 20, bottom: 10),
                  child: LineChart(
                    LineChartData(
                      gridData: const FlGridData(show: false),
                      titlesData: const FlTitlesData(
                        show: true,
                        topTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)),
                        rightTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)),
                        bottomTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)),
                        leftTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)),
                      ),
                      borderData: FlBorderData(show: false),
                      lineBarsData: [
                        LineChartBarData(
                          spots: (data!['history'] as List).asMap().entries.map((e) {
                            return FlSpot(e.key.toDouble(), e.value is double ? e.value : (e.value as num).toDouble());
                          }).toList(),
                          isCurved: true,
                          color: Colors.blueAccent,
                          barWidth: 3,
                          isStrokeCapRound: true,
                          dotData: const FlDotData(show: false),
                          belowBarData: BarAreaData(
                            show: true,
                            color: Colors.blueAccent.withOpacity(0.15),
                          ),
                        ),
                      ],
                    ),
                  ),
                )
              : const Center(child: Text("No hay datos históricos disponibles", style: TextStyle(color: Colors.grey))),
          ),
        ],
      ),
    );
  }

  Widget _buildAIRecommendationCard() {
    // Lógica dinámica basada en la respuesta de smart_recommendation de tu Python
    bool isBuy = data!['recomendacion'].toString().toLowerCase().contains("comprar");
    
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
                  "RECOMENDACIÓN",
                  style: GoogleFonts.poppins(fontSize: 12, fontWeight: FontWeight.bold, color: Colors.black54),
                ),
                Text(
                  data!['recomendacion'].toString().toUpperCase(),
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

  Future<void> _sendDecision(String decision) async {
    try {
      final response = await http.post(
        Uri.parse('http://127.0.0.1:8000/decision'),
        headers: {"Content-Type": "application/json"},
        body: json.encode({
          "ticker": widget.ticker,
          "decision": decision
        }),
      );

      if (response.statusCode == 200) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text("Decisión '$decision' registrada correctamente"), backgroundColor: Colors.green),
        );
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text("Error al registrar: ${response.body}"), backgroundColor: Colors.red),
        );
      }
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text("Error de conexión: $e"), backgroundColor: Colors.red),
      );
    }
  }

  Widget _buildDecisionButtons() {
    return Row(
      children: [
        Expanded(
          child: OutlinedButton(
            onPressed: () => _sendDecision("No compré"), 
            style: OutlinedButton.styleFrom(
              padding: const EdgeInsets.symmetric(vertical: 15), 
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(15))
            ),
            child: const Text("No comprar"),
          ),
        ),
        const SizedBox(width: 15),
        Expanded(
          child: ElevatedButton(
            onPressed: () => _sendDecision("Compré"), 
            style: ElevatedButton.styleFrom(
              backgroundColor: Colors.blueAccent,
              padding: const EdgeInsets.symmetric(vertical: 15),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(15))
            ),
            child: const Text("Comprar"),
          ),
        ),
      ],
    );
  }
}