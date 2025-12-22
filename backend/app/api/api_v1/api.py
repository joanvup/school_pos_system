from fastapi import APIRouter
from app.api.api_v1.endpoints import users, auth, students, data_import, cards, products, sales, recharges, reports, purchases, categories, stock, settings

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Autenticación"])
api_router.include_router(users.router, prefix="/users", tags=["Usuarios"])
api_router.include_router(students.router, prefix="/students", tags=["Estudiantes"])
api_router.include_router(data_import.router, prefix="/import", tags=["Carga Masiva"])
api_router.include_router(cards.router, prefix="/cards", tags=["Tarjetas RFID"])
api_router.include_router(products.router, prefix="/products", tags=["Inventario"])
api_router.include_router(sales.router, prefix="/sales", tags=["Ventas POS"])
api_router.include_router(recharges.router, prefix="/recharges", tags=["Pagos PSE"])
api_router.include_router(reports.router, prefix="/reports", tags=["Reportes"]) 
api_router.include_router(purchases.router, prefix="/purchases", tags=["Compras/Entradas"])
api_router.include_router(categories.router, prefix="/categories", tags=["Categorias"])
api_router.include_router(stock.router, prefix="/stock-adjustments", tags=["Ajustes Inventory"])
api_router.include_router(settings.router, prefix="/settings", tags=["Configuración Sistema"])