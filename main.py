import os
import sys
import argparse
import yaml
from typing import Dict, Any, Optional


class ConfigError(Exception):
    pass


class ConfigLoader:
    
    def __init__(self):
        self.config: Dict[str, Any] = {}
        self.required_fields = [
            'package_name',
            'repository_url', 
            'test_repository_mode',
            'package_version',
            'output_filename',
            'ascii_tree_output',
            'max_dependency_depth'  
        ]
    
    def load_config(self, config_path: Optional[str] = None) -> Dict[str, Any]:
        if config_path is None:
            default_path = os.path.join(os.path.dirname(__file__), 'def.yaml')
            config_path = os.path.abspath(default_path)
        
        if not os.path.exists(config_path):
            raise ConfigError(f"Конфигурационный файл не найден: {config_path}")
        
        try:
            with open(config_path, 'r', encoding='utf-8') as file:
                self.config = yaml.safe_load(file)
        except yaml.YAMLError as e:
            raise ConfigError(f"Ошибка парсинга YAML: {e}")
        except Exception as e:
            raise ConfigError(f"Ошибка чтения файла: {e}")

        self._validate_config()
        return self.config
    
    def _validate_config(self) -> None:
        if self.config is None:
            raise ConfigError("Конфигурационный файл пуст")
        
        for field in self.required_fields:
            if field not in self.config:
                raise ConfigError(f"Отсутствует обязательное поле: {field}")
        
        if self.config['max_dependency_depth'] < 1:
            raise ConfigError("Максимальная глубина анализа должна быть положительным числом")


class DependencyVisualizer:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
    
    def display_config(self) -> None:
        print("НАСТРАИВАЕМЫЕ ПАРАМЕТРЫ КОНФИГУРАЦИИ")
        
        config_items = [
            ("Имя анализируемого пакета", "package_name"),
            ("URL-адрес репозитория", "repository_url"),
            ("Режим работы с тестовым репозиторием", "test_repository_mode"),
            ("Версия пакета", "package_version"),
            ("Имя файла с изображением графа", "output_filename"),
            ("Режим вывода ASCII-дерева", "ascii_tree_output"),
            ("Максимальная глубина анализа", "max_dependency_depth")
        ]
        
        for description, key in config_items:
            value = self.config[key]
            print(f"{description:40}: {value}")
    
    def run(self) -> None:
        print("Визуализатор графа зависимостей пакетов")
        print()
        self.display_config()


def demonstrate_error_handling():
    print("ДЕМОНСТРАЦИЯ ОБРАБОТКИ ОШИБОК")
    print()
    
    loader = ConfigLoader()
    
    test_cases = [
        {
            "name": "Несуществующий файл",
            "config_path": "nonexistent.yaml",
            "expected_error": "Конфигурационный файл не найден"
        },
        {
            "name": "Некорректный YAML",
            "config_content": "invalid: yaml: : :",
            "expected_error": "Ошибка парсинга YAML"
        },
        {
            "name": "Отсутствует поле",
            "config_content": {"package_name": "test"},
            "expected_error": "Отсутствует обязательное поле"
        },
        {
            "name": "Некорректная глубина",
            "config_content": {
                "package_name": "test",
                "repository_url": "http://test.com",
                "test_repository_mode": False,
                "package_version": "1.0",
                "output_filename": "test.png",
                "ascii_tree_output": True,
                "max_dependency_depth": 0
            },
            "expected_error": "Максимальная глубина анализа должна быть положительным числом"
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\nТест {i}: {test_case['name']}")
        
        try:
            if "config_content" in test_case:
                test_file = f"test_config_{i}.yaml"
                with open(test_file, 'w') as f:
                    yaml.dump(test_case["config_content"], f)
                loader.load_config(test_file)
                os.remove(test_file)
            else:
                loader.load_config(test_case["config_path"])

        except ConfigError as e:
            print(f" Обработана: {e}")


def main():
    parser = argparse.ArgumentParser()
    
    parser.add_argument(
        '-c', '--config',
        type=str
    )
    
    parser.add_argument(
        '--test-errors',
        action='store_true'
    )
    
    args = parser.parse_args()
    
    if args.test_errors:
        demonstrate_error_handling()
        return
    
    try:
        config_loader = ConfigLoader()
        config = config_loader.load_config(args.config)
        visualizer = DependencyVisualizer(config)
        visualizer.run()
        
    except ConfigError as e:
        print(f"Ошибка конфигурации: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Ошибка: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()