"""
FrigoScan — Router Statistiques et Historique.
"""

from fastapi import APIRouter
from server.database import get_db, rows_to_list
from datetime import datetime, date, timedelta

router = APIRouter(prefix="/api/stats", tags=["Statistiques"])


@router.get("/consumption")
def consumption_history(days: int = 30, user_name: str = None):
    """Historique des consommations."""
    db = get_db()
    try:
        since = (date.today() - timedelta(days=days)).isoformat()
        if user_name:
            rows = db.execute(
                "SELECT * FROM consumption_history WHERE consumed_at >= ? AND user_name = ? ORDER BY consumed_at DESC",
                (since, user_name)
            ).fetchall()
        else:
            rows = db.execute(
                "SELECT * FROM consumption_history WHERE consumed_at >= ? ORDER BY consumed_at DESC",
                (since,)
            ).fetchall()
        return {"success": True, "history": rows_to_list(rows)}
    finally:
        db.close()


@router.get("/summary")
def stats_summary(days: int = 30):
    """Statistiques résumées."""
    db = get_db()
    try:
        since = (date.today() - timedelta(days=days)).isoformat()

        # Total consommés
        consumed = db.execute(
            "SELECT COUNT(*) as c FROM consumption_history WHERE consumed_at >= ?", (since,)
        ).fetchone()["c"]

        # Par catégorie
        by_category = rows_to_list(db.execute(
            "SELECT category, COUNT(*) as count, SUM(quantity) as total_qty FROM consumption_history WHERE consumed_at >= ? GROUP BY category ORDER BY count DESC",
            (since,)
        ).fetchall())

        # Produits les plus consommés
        top_products = rows_to_list(db.execute(
            "SELECT product_name, COUNT(*) as count FROM consumption_history WHERE consumed_at >= ? GROUP BY product_name ORDER BY count DESC LIMIT 10",
            (since,)
        ).fetchall())

        # Produits gaspillés (expirés/supprimés)
        wasted = db.execute(
            "SELECT COUNT(*) as c FROM fridge_items WHERE status IN ('expired', 'removed') AND added_at >= ?",
            (since,)
        ).fetchone()["c"]

        # Consommation par jour de la semaine
        by_day = rows_to_list(db.execute(
            """SELECT 
                CASE CAST(strftime('%w', consumed_at) AS INTEGER)
                    WHEN 0 THEN 'Dimanche' WHEN 1 THEN 'Lundi' WHEN 2 THEN 'Mardi'
                    WHEN 3 THEN 'Mercredi' WHEN 4 THEN 'Jeudi' WHEN 5 THEN 'Vendredi'
                    WHEN 6 THEN 'Samedi'
                END as day_name,
                COUNT(*) as count
               FROM consumption_history WHERE consumed_at >= ?
               GROUP BY strftime('%w', consumed_at) ORDER BY strftime('%w', consumed_at)""",
            (since,)
        ).fetchall())

        # Consommation par mois
        by_month = rows_to_list(db.execute(
            "SELECT strftime('%Y-%m', consumed_at) as month, COUNT(*) as count FROM consumption_history GROUP BY month ORDER BY month DESC LIMIT 12"
        ).fetchall())

        return {
            "success": True,
            "period_days": days,
            "total_consumed": consumed,
            "total_wasted": wasted,
            "by_category": by_category,
            "top_products": top_products,
            "by_day_of_week": by_day,
            "by_month": by_month,
        }
    finally:
        db.close()


@router.get("/waste")
def waste_stats(days: int = 30):
    """Statistiques de gaspillage."""
    db = get_db()
    try:
        since = (date.today() - timedelta(days=days)).isoformat()
        expired = rows_to_list(db.execute(
            "SELECT name, category, dlc, added_at FROM fridge_items WHERE status='expired' AND added_at >= ? ORDER BY dlc",
            (since,)
        ).fetchall())
        removed = rows_to_list(db.execute(
            "SELECT name, category, added_at FROM fridge_items WHERE status='removed' AND added_at >= ?",
            (since,)
        ).fetchall())
        return {
            "success": True,
            "expired_products": expired,
            "removed_products": removed,
            "total_wasted": len(expired) + len(removed),
        }
    finally:
        db.close()
