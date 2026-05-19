class StockModel {
  final String ticker;
  final String nombre;
  double precio;
  double variacion;
  bool colorGreen;
  double volumen;
  double marketCap;
  List<double> history;

  StockModel({
    required this.ticker,
    required this.nombre,
    required this.precio,
    required this.variacion,
    required this.colorGreen,
    required this.volumen,
    required this.marketCap,
    required this.history,
  });

  factory StockModel.fromJson(Map<String, dynamic> json) {
    // Manejar diferentes posibles nombres de campos de la API
    return StockModel(
      ticker: json['ticker'] ?? '',
      nombre: json['nombre'] ?? json['name'] ?? '',
      precio: (json['precio'] ?? json['price'] ?? 0.0).toDouble(),
      variacion: (json['variacion'] ?? json['change_percent'] ?? 0.0).toDouble(),
      colorGreen: (json['colorGreen'] ?? ((json['variacion'] ?? 0.0) >= 0)),
      volumen: (json['volumen'] ?? json['volume'] ?? 0.0).toDouble(),
      marketCap: (json['marketCap'] ?? json['market_cap'] ?? 0.0).toDouble(),
      history: (json['history'] as List? ?? []).map((e) => (e as num).toDouble()).toList(),
    );
  }

  void updateFromSocket(Map<String, dynamic> data) {
    if (data['price'] != null) precio = (data['price'] as num).toDouble();
    if (data['change_percent'] != null) {
      variacion = (data['change_percent'] as num).toDouble();
      colorGreen = variacion >= 0;
    }
    if (data['volume'] != null) volumen = (data['volume'] as num).toDouble();
  }
}
