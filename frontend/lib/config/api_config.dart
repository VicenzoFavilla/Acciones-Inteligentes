class ApiConfig {
  // Cuando pases a producción, solo cambias esto a "https://api.tu-dominio.com"
  static const String baseUrl = 'http://127.0.0.1:8001';
  static const String wsUrl = 'ws://127.0.0.1:8001/ws/market';
  
  // Opcional: Métodos helpers para construir URLs
  static Uri buildUri(String path, [Map<String, dynamic>? queryParameters]) {
    final uri = Uri.parse('$baseUrl$path');
    if (queryParameters != null && queryParameters.isNotEmpty) {
      final stringParams = queryParameters.map((key, value) => MapEntry(key, value.toString()));
      return uri.replace(queryParameters: stringParams);
    }
    return uri;
  }
}
