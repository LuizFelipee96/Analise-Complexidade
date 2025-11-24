from parsers.gtfs_parser import GTFSParser

parser = GTFSParser('./data/gtfs/')
parser.carregar_dados()

print(f"✓ Paradas carregadas: {len(parser.stops)}")
print(f"✓ Rotas carregadas: {len(parser.routes)}")
print(f"✓ Viagens: {len(parser.trips)}")
print(f"✓ Horários: {len(parser.stop_times)}")

recife_stops = parser.stops[
    (parser.stops['stop_lat'] >= -8.2) &
    (parser.stops['stop_lat'] <= -7.9) &
    (parser.stops['stop_lon'] >= -35.05) &
    (parser.stops['stop_lon'] <= -34.85)
]

print(f"\n📍 Paradas na região de Recife: {len(recife_stops)}")
print("\nAlgumas paradas:")
print(recife_stops[['stop_name', 'stop_lat', 'stop_lon']].head(10))
