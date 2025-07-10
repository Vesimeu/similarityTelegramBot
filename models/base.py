from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, declared_attr


class Base(DeclarativeBase):
    __abstract__ = True

    @declared_attr.directive
    def __tablename__(self) -> str:
        table_name: str = self.__name__.lower()
        return f"{table_name[:-1]}ies" if table_name[-1] == "y" else f"{table_name}s"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
        sort_order=-10,
    )
