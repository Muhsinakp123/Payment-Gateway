from django.db import models

class Product(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.name


class Order(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True)
    status = models.CharField(max_length=20, default='PENDING')  
    currency = models.CharField(max_length=3, default="USD")  # Add this line
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # auto calculate price
        self.total_price = self.product.price * self.quantity
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Order {self.id} - {self.status}"


class Transaction(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    payment_id = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Transaction {self.payment_id}"

