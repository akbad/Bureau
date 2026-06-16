from operations.mcp_catalog import resolve_mcp_catalog


def test_resolves_enabled_servers_with_cli_overrides():
    config = {
        "mcp": {
            "client_configs": {
                "context7": {
                    "enabled": True,
                    "clients": {
                        "default": {
                            "transport": "http",
                            "url": "https://x/${API_KEY}",
                        },
                        "codex": {
                            "transport": "stdio",
                            "command": ["npx", "-y", "@upstash/context7-mcp"],
                        },
                    },
                    "requires_env": ["API_KEY"],
                }
            }
        }
    }
    env = {"API_KEY": "k"}

    resolved = resolve_mcp_catalog(config, env=env)
    assert resolved["client_configs"]["context7"]["clients"]["default"]["url"] == "https://x/k"
    assert (
        resolved["client_configs"]["context7"]["clients"]["codex"]["transport"]
        == "stdio"
    )


def test_filters_disabled_and_missing_env():
    config = {
        "mcp": {
            "client_configs": {
                "a": {
                    "enabled": False,
                    "clients": {
                        "default": {"transport": "http", "url": "http://a"}
                    },
                },
                "b": {
                    "enabled": True,
                    "requires_env": ["MISSING"],
                    "clients": {
                        "default": {"transport": "http", "url": "http://b"}
                    },
                },
            }
        }
    }
    resolved = resolve_mcp_catalog(config, env={})
    assert "a" not in resolved["client_configs"]
    assert "b" not in resolved["client_configs"]


def test_expands_server_fields_and_nested_placeholders():
    config = {
        "path_to": {"workspace": "/tmp/workspace"},
        "mcp": {
            "client_configs": {
                "fs": {
                    "enabled": True,
                    "settings": {"whitelist": "${path_to.workspace}"},
                    "clients": {
                        "default": {
                            "transport": "stdio",
                            "command": [
                                "echo",
                                "${mcp.client_configs.fs.settings.whitelist}",
                            ],
                        }
                    },
                }
            }
        },
    }

    resolved = resolve_mcp_catalog(config, env={})

    assert resolved["client_configs"]["fs"]["settings"]["whitelist"] == "/tmp/workspace"
    assert resolved["client_configs"]["fs"]["clients"]["default"]["command"][1] == "/tmp/workspace"


def test_filters_servers_with_missing_service_dependencies():
    config = {
        "mcp": {
            "services": {
                "svc": {
                    "enabled": False,
                    "kind": "http_process",
                    "port": 1,
                }
            },
            "client_configs": {
                "a": {
                    "enabled": True,
                    "depends_on": {"services": ["svc"]},
                    "clients": {
                        "default": {"transport": "http", "url": "http://x"}
                    },
                }
            },
        }
    }

    resolved = resolve_mcp_catalog(config, env={})

    assert "a" not in resolved["client_configs"]


def test_resolves_dependencies_and_expands_placeholders():
    config = {
        "path_to": {"mcp_clones": "/tmp/mcp"},
        "mcp": {
            "dependencies": {
                "git_dep": {
                    "enabled": True,
                    "kind": "git_repo",
                    "repo_url": "https://github.com/test/repo.git",
                    "path": "${path_to.mcp_clones}/test-repo",
                },
                "storage_dep": {
                    "enabled": True,
                    "kind": "file",
                    "path": "~/.test/storage.db",
                },
            },
            "services": {
                "svc": {
                    "enabled": True,
                    "kind": "http_process",
                    "port": 8080,
                    "depends_on": {"dependencies": ["git_dep"]},
                    "command": ["run", "${mcp.dependencies.git_dep.path}"],
                }
            },
            "client_configs": {
                "srv": {
                    "enabled": True,
                    "depends_on": {"dependencies": ["storage_dep"]},
                    "clients": {
                        "default": {
                            "transport": "http",
                            "url": "http://localhost:8080",
                        }
                    },
                }
            },
        }
    }

    resolved = resolve_mcp_catalog(config, env={})

    # Dependencies should be resolved and placeholders expanded
    assert "git_dep" in resolved["dependencies"]
    assert resolved["dependencies"]["git_dep"]["path"] == "/tmp/mcp/test-repo"
    assert "storage_dep" in resolved["dependencies"]
    assert resolved["dependencies"]["storage_dep"]["path"] == "~/.test/storage.db"

    # Services should reference resolved dependency paths
    assert "svc" in resolved["services"]
    assert resolved["services"]["svc"]["command"][1] == "/tmp/mcp/test-repo"

    # Servers should be included when dependencies are met
    assert "srv" in resolved["client_configs"]


def test_filesystem_allowed_methods_override_command():
    config = {
        "mcp": {
            "client_configs": {
                "filesystem": {
                    "enabled": True,
                    "settings": {
                        "allowed_methods": [
                            "read_multiple_files",
                            "read_file",
                        ]
                    },
                    "clients": {
                        "default": {
                            "transport": "stdio",
                            "command": [
                                "/tmp/npm-tools/node_modules/.bin/mcp-filter",
                                "--include",
                                "read_multiple_files",
                                "--",
                                "/tmp/npm-tools/node_modules/.bin/mcp-server-filesystem",
                                "/tmp",
                            ],
                        }
                    },
                }
            }
        }
    }

    resolved = resolve_mcp_catalog(config, env={})
    command = resolved["client_configs"]["filesystem"]["clients"]["default"]["command"]

    assert command.count("--include") == 2
    assert command[:7] == [
        "/tmp/npm-tools/node_modules/.bin/mcp-filter",
        "--include",
        "read_multiple_files",
        "--include",
        "read_file",
        "--",
        "/tmp/npm-tools/node_modules/.bin/mcp-server-filesystem",
    ]
    assert command[-1] == "/tmp"


def test_filters_services_with_missing_dependency_dependencies():
    config = {
        "mcp": {
            "dependencies": {
                "dep": {"enabled": False, "kind": "git_repo"}
            },
            "services": {
                "svc": {
                    "enabled": True,
                    "kind": "http_process",
                    "port": 8080,
                    "depends_on": {"dependencies": ["dep"]},
                }
            },
        }
    }

    resolved = resolve_mcp_catalog(config, env={})

    assert "svc" not in resolved["services"]


def test_filters_servers_with_missing_dependency_dependencies():
    config = {
        "mcp": {
            "dependencies": {
                "dep": {"enabled": False, "kind": "file"}
            },
            "client_configs": {
                "srv": {
                    "enabled": True,
                    "depends_on": {"dependencies": ["dep"]},
                    "clients": {"default": {"transport": "http", "url": "http://x"}},
                }
            },
        }
    }

    resolved = resolve_mcp_catalog(config, env={})

    assert "srv" not in resolved["client_configs"]


def test_crawl4ai_dependency_placeholders_expand():
    config = {
        "path_to": {"mcp_clones": "/tmp/mcp-clones"},
        "mcp": {
            "dependencies": {
                "crawl4ai_mcp_repo": {
                    "enabled": True,
                    "kind": "git_repo",
                    "repo_url": "https://github.com/sadiuysal/crawl4ai-mcp-server.git",
                    "path": "${path_to.mcp_clones}/crawl4ai-mcp-server",
                }
            },
            "client_configs": {
                "crawl4ai-mcp-server": {
                    "enabled": True,
                    "depends_on": {"dependencies": ["crawl4ai_mcp_repo"]},
                    "settings": {
                        "image": "bureau/crawl4ai-mcp-server:c3c3b43",
                        "host_output_dir": "/tmp/crawl4ai",
                        "container_output_dir": "/app/crawls",
                    },
                    "clients": {
                        "default": {
                            "transport": "stdio",
                            "command": [
                                "docker",
                                "run",
                                "--volume",
                                "${mcp.client_configs.crawl4ai-mcp-server.settings.host_output_dir}:${mcp.client_configs.crawl4ai-mcp-server.settings.container_output_dir}",
                                "${mcp.client_configs.crawl4ai-mcp-server.settings.image}",
                            ],
                        }
                    },
                }
            },
        },
    }

    resolved = resolve_mcp_catalog(config, env={})

    assert (
        resolved["dependencies"]["crawl4ai_mcp_repo"]["path"]
        == "/tmp/mcp-clones/crawl4ai-mcp-server"
    )
    command = resolved["client_configs"]["crawl4ai-mcp-server"]["clients"]["default"]["command"]
    assert "/tmp/crawl4ai:/app/crawls" in command
    assert command[-1] == "bureau/crawl4ai-mcp-server:c3c3b43"


def test_crawl4ai_client_filtered_when_dependency_disabled():
    config = {
        "mcp": {
            "dependencies": {
                "crawl4ai_mcp_repo": {
                    "enabled": False,
                    "kind": "git_repo",
                    "repo_url": "https://github.com/sadiuysal/crawl4ai-mcp-server.git",
                    "path": "/tmp/crawl4ai-mcp-server",
                }
            },
            "client_configs": {
                "crawl4ai-mcp-server": {
                    "enabled": True,
                    "depends_on": {"dependencies": ["crawl4ai_mcp_repo"]},
                    "clients": {
                        "default": {
                            "transport": "stdio",
                            "command": ["docker", "run", "image"],
                        }
                    },
                }
            },
        },
    }

    resolved = resolve_mcp_catalog(config, env={})

    assert "crawl4ai-mcp-server" not in resolved["client_configs"]


def test_filters_services_with_disabled_service_dependency():
    """Service depending on a disabled peer service is skipped."""
    config = {
        "mcp": {
            "services": {
                "db": {"enabled": False, "kind": "docker_container"},
                "api": {
                    "enabled": True,
                    "kind": "http_process",
                    "port": 8080,
                    "depends_on": {"services": ["db"]},
                },
            }
        }
    }
    resolved = resolve_mcp_catalog(config, env={})
    assert "api" not in resolved["services"]
    assert "db" not in resolved["services"]


def test_resolves_services_in_dependency_order():
    """Service depending on an enabled peer is resolved."""
    config = {
        "mcp": {
            "services": {
                "db": {"enabled": True, "kind": "docker_container"},
                "api": {
                    "enabled": True,
                    "kind": "http_process",
                    "port": 8080,
                    "depends_on": {"services": ["db"]},
                },
            }
        }
    }
    resolved = resolve_mcp_catalog(config, env={})
    assert "db" in resolved["services"]
    assert "api" in resolved["services"]


def test_cascading_service_disable():
    """If A depends on B depends on C, disabling C skips B and A."""
    config = {
        "mcp": {
            "services": {
                "c": {"enabled": False, "kind": "docker_container"},
                "b": {
                    "enabled": True,
                    "kind": "http_process",
                    "port": 1,
                    "depends_on": {"services": ["c"]},
                },
                "a": {
                    "enabled": True,
                    "kind": "http_process",
                    "port": 2,
                    "depends_on": {"services": ["b"]},
                },
            }
        }
    }
    resolved = resolve_mcp_catalog(config, env={})
    assert resolved["services"] == {}


def test_disabled_for_preserved_through_resolution():
    """disabled_for list survives the resolve pipeline without error."""
    config = {
        "mcp": {
            "client_configs": {
                "srv": {
                    "enabled": True,
                    "clients": {
                        "disabled_for": ["codex"],
                        "default": {"transport": "http", "url": "http://localhost:8080"},
                    },
                }
            }
        }
    }
    resolved = resolve_mcp_catalog(config, env={})
    assert resolved["client_configs"]["srv"]["clients"]["disabled_for"] == ["codex"]


def test_disabled_for_does_not_crash_resolution():
    """Resolution must not call dict() on the disabled_for list."""
    config = {
        "mcp": {
            "client_configs": {
                "srv": {
                    "enabled": True,
                    "clients": {
                        "disabled_for": ["codex", "gemini"],
                        "default": {"transport": "http", "url": "http://x"},
                        "claude": {"transport": "stdio", "command": ["test"]},
                    },
                }
            }
        }
    }
    resolved = resolve_mcp_catalog(config, env={})
    assert "default" in resolved["client_configs"]["srv"]["clients"]
    assert "claude" in resolved["client_configs"]["srv"]["clients"]


class TestDependencyRequiresOrdering:
    """W11: dependencies resolve in topological order based on requires."""

    def test_requires_ordering(self):
        """overlay requires base — base must resolve first."""
        config = {
            "mcp": {
                "dependencies": {
                    "overlay": {"kind": "file", "path": "/y", "requires": ["base"], "enabled": True},
                    "base": {"kind": "file", "path": "/x", "enabled": True},
                },
                "services": {},
                "client_configs": {},
            }
        }
        result = resolve_mcp_catalog(config, env={})
        dep_names = list(result["dependencies"].keys())
        assert dep_names.index("base") < dep_names.index("overlay")

    def test_requires_missing_dep_skips(self):
        """If a required dep is disabled, the requiring dep is skipped."""
        config = {
            "mcp": {
                "dependencies": {
                    "base": {"kind": "file", "path": "/x", "enabled": False},
                    "overlay": {"kind": "file", "path": "/y", "requires": ["base"], "enabled": True},
                },
                "services": {},
                "client_configs": {},
            }
        }
        result = resolve_mcp_catalog(config, env={})
        assert "overlay" not in result["dependencies"]
        assert "base" not in result["dependencies"]

    def test_chain_ordering(self):
        """c requires b requires a — all three must resolve in order."""
        config = {
            "mcp": {
                "dependencies": {
                    "c": {"kind": "file", "path": "/z", "requires": ["b"], "enabled": True},
                    "a": {"kind": "file", "path": "/x", "enabled": True},
                    "b": {"kind": "file", "path": "/y", "requires": ["a"], "enabled": True},
                },
                "services": {},
                "client_configs": {},
            }
        }
        result = resolve_mcp_catalog(config, env={})
        dep_names = list(result["dependencies"].keys())
        assert dep_names.index("a") < dep_names.index("b")
        assert dep_names.index("b") < dep_names.index("c")

    def test_no_requires_preserves_all(self):
        """Dependencies without requires all resolve normally."""
        config = {
            "mcp": {
                "dependencies": {
                    "x": {"kind": "file", "path": "/x", "enabled": True},
                    "y": {"kind": "file", "path": "/y", "enabled": True},
                },
                "services": {},
                "client_configs": {},
            }
        }
        result = resolve_mcp_catalog(config, env={})
        assert "x" in result["dependencies"]
        assert "y" in result["dependencies"]


class TestAutoDetectedDependencyResolution:
    """W6: auto-detected deps affect enablement gating in resolution."""

    def test_client_config_skipped_when_inferred_service_disabled(self):
        """If qdrant client_config references qdrant_mcp service via placeholder,
        and qdrant_mcp is disabled, qdrant should be skipped even without explicit depends_on."""
        config = {
            "mcp": {
                "services": {
                    "qdrant_mcp": {"kind": "docker_container", "image": "qdrant",
                                   "host_port": 6333, "container_port": 6333,
                                   "enabled": False},
                },
                "client_configs": {
                    "qdrant": {"clients": {"default": {
                        "transport": "http",
                        "url": "http://localhost:${mcp.services.qdrant_mcp.host_port}/",
                    }}},
                },
                "dependencies": {},
            }
        }
        result = resolve_mcp_catalog(config, env={})
        assert "qdrant" not in result["client_configs"]

    def test_client_config_kept_when_inferred_service_enabled(self):
        config = {
            "mcp": {
                "services": {
                    "qdrant_mcp": {"kind": "docker_container", "image": "qdrant",
                                   "host_port": 6333, "container_port": 6333},
                },
                "client_configs": {
                    "qdrant": {"clients": {"default": {
                        "transport": "http",
                        "url": "http://localhost:${mcp.services.qdrant_mcp.host_port}/",
                    }}},
                },
                "dependencies": {},
            }
        }
        result = resolve_mcp_catalog(config, env={})
        assert "qdrant" in result["client_configs"]

    def test_explicit_depends_on_unions_with_inferred(self):
        """Explicit depends_on adds to inferred, never subtracts."""
        config = {
            "mcp": {
                "services": {
                    "svc_a": {"kind": "http_process", "port": 1, "command": ["x"]},
                    "svc_b": {"kind": "http_process", "port": 2, "command": ["y"],
                              "enabled": False},
                },
                "client_configs": {
                    "client": {
                        "depends_on": {"services": ["svc_b"]},
                        "clients": {"default": {
                            "transport": "http",
                            "url": "http://localhost:${mcp.services.svc_a.port}/",
                        }},
                    },
                },
                "dependencies": {},
            }
        }
        result = resolve_mcp_catalog(config, env={})
        # svc_b disabled → explicit dep fails → client skipped
        assert "client" not in result["client_configs"]
