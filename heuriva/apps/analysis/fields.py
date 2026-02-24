import zstandard as zstd
from django.conf import settings
from django.db import models


class ZstdCompressedTextField(models.BinaryField):
    """
    Field with Zstandard compression and decompressed content cache.
    Compression level configured in settings.ZSTD_COMPRESSION_LEVEL
    """

    def contribute_to_class(self, cls, name, **kwargs):
        """
        Adds the field to the model and creates a private cache attribute.
        """
        super().contribute_to_class(cls, name, **kwargs)

        # Private cache attribute name
        cache_attr = f"_cached_{name}"

        # Replace default descriptor with one that uses cache
        setattr(cls, name, CachedCompressedDescriptor(self, cache_attr))

    def get_prep_value(self, value):
        if value is None:
            return value
        if isinstance(value, str):
            value = value.encode("utf-8")

        compression_level = getattr(settings, "ZSTD_COMPRESSION_LEVEL", 5)
        cctx = zstd.ZstdCompressor(level=compression_level)
        return cctx.compress(value)

    def from_db_value(self, value, expression, connection):
        if value is None:
            return value

        dctx = zstd.ZstdDecompressor()
        return dctx.decompress(value).decode("utf-8")

    def to_python(self, value):
        if isinstance(value, str):
            return value
        if value is None:
            return value

        dctx = zstd.ZstdDecompressor()
        return dctx.decompress(value).decode("utf-8")


class CachedCompressedDescriptor:
    """
    Descriptor that caches the decompressed value in the model instance.
    """

    def __init__(self, field, cache_attr):
        self.field = field
        self.cache_attr = cache_attr

    def __get__(self, instance, owner):
        if instance is None:
            return self

        # Check if already in cache
        if hasattr(instance, self.cache_attr):
            return getattr(instance, self.cache_attr)

        # Fetch compressed value from database
        compressed_value = instance.__dict__.get(self.field.attname)

        if compressed_value is None:
            decompressed_value = None
        else:
            # compressed_value should be bytes from the database
            if isinstance(compressed_value, str):
                # If it's already a string, it's already decompressed
                decompressed_value = compressed_value
            else:
                # Decompress bytes
                dctx = zstd.ZstdDecompressor()
                decompressed_value = dctx.decompress(compressed_value).decode("utf-8")

        # Store in cache
        setattr(instance, self.cache_attr, decompressed_value)

        return decompressed_value

    def __set__(self, instance, value):
        # Clear cache when assigning new value
        if hasattr(instance, self.cache_attr):
            delattr(instance, self.cache_attr)

        # Set value (will be compressed by get_prep_value)
        instance.__dict__[self.field.attname] = value
