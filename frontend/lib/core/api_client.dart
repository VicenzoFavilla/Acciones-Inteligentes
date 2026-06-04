import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import '../config/api_config.dart';
import 'dart:convert';
import 'package:flutter/material.dart';

class ApiClient {
  // Obtiene las cabeceras comunes e inyecta el token de autenticación si existe
  static Future<Map<String, String>> _getHeaders() async {
    final prefs = await SharedPreferences.getInstance();
    final token = prefs.getString('auth_token');
    return {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      if (token != null) 'Authorization': 'Bearer $token',
    };
  }

  // Realiza una petición GET
  static Future<http.Response> get(String path) async {
    try {
      final uri = ApiConfig.buildUri(path);
      final headers = await _getHeaders();
      final response = await http.get(uri, headers: headers);
      await _checkUnauthorized(response);
      return response;
    } catch (e) {
      debugPrint("ApiClient GET error: $e");
      rethrow;
    }
  }

  // Realiza una petición POST
  static Future<http.Response> post(String path, {Object? body}) async {
    try {
      final uri = ApiConfig.buildUri(path);
      final headers = await _getHeaders();
      final response = await http.post(
        uri,
        headers: headers,
        body: body != null ? json.encode(body) : null,
      );
      await _checkUnauthorized(response);
      return response;
    } catch (e) {
      debugPrint("ApiClient POST error: $e");
      rethrow;
    }
  }

  // Realiza una petición PUT
  static Future<http.Response> put(String path, {Object? body}) async {
    try {
      final uri = ApiConfig.buildUri(path);
      final headers = await _getHeaders();
      final response = await http.put(
        uri,
        headers: headers,
        body: body != null ? json.encode(body) : null,
      );
      await _checkUnauthorized(response);
      return response;
    } catch (e) {
      debugPrint("ApiClient PUT error: $e");
      rethrow;
    }
  }

  // Realiza una petición DELETE
  static Future<http.Response> delete(String path) async {
    try {
      final uri = ApiConfig.buildUri(path);
      final headers = await _getHeaders();
      final response = await http.delete(uri, headers: headers);
      await _checkUnauthorized(response);
      return response;
    } catch (e) {
      debugPrint("ApiClient DELETE error: $e");
      rethrow;
    }
  }

  // Intercepta respuestas 401 (No autorizado) para limpiar la sesión expirada
  static Future<void> _checkUnauthorized(http.Response response) async {
    if (response.statusCode == 401) {
      debugPrint("Sesión expirada o token inválido (401). Limpiando datos de sesión local...");
      final prefs = await SharedPreferences.getInstance();
      await prefs.remove('auth_token');
      await prefs.remove('user_email');
      await prefs.remove('user_name');
      // Opcional: Se puede implementar un despachador de eventos si se requiere redirigir reactivamente
    }
  }
}
