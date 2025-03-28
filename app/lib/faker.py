from faker import Faker

# fake = Faker("en_US")


class CustomFaker(Faker):
    """Wrap Faker class to add custom methods."""

    def title(self, word_count: int = 3):
        """Create a fake display name with specified word count."""

        return self.sentence(nb_words=word_count).title()


fake = CustomFaker("en_US")

__all__ = ["fake"]
