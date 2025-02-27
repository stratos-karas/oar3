
def estimate_job_nb_resources_in_spread(session, config, resource_request, j_properties):
    """returns an array with an estimation of the number of resources that can be used by a job:
    (resources_available, [(nbresources => int, walltime => int)])
    """
    # estimate_job_nb_resources
    estimated_nb_resources = []
    is_resource_available = False
    resource_set = ResourceSet(session, config)
    resources_itvs = resource_set.roid_itvs

    for mld_idx, mld_resource_request in enumerate(resource_request):
        resource_desc, walltime = mld_resource_request

        if not walltime:
            walltime = str(config["DEFAULT_JOB_WALLTIME"])

        estimated_nb_res = 0

        for prop_res in resource_desc:
            jrg_grp_property = prop_res["property"]
            resource_value_lst = prop_res["resources"]

            #
            # determine resource constraints
            #
            if (not j_properties) and (
                not jrg_grp_property or (jrg_grp_property == "type='default'")
            ):  # TODO change to re.match
                # copy itvs
                constraints = copy.copy(resource_set.roid_itvs)
            else:
                and_sql = ""
                if j_properties and jrg_grp_property:
                    and_sql = " AND "
                if j_properties is None:
                    j_properties = ""
                if jrg_grp_property is None:
                    jrg_grp_property = ""

                sql_constraints = j_properties + and_sql + jrg_grp_property

                try:
                    request_constraints = (
                        session.query(Resource.id).filter(text(sql_constraints)).all()
                    )
                except exc.SQLAlchemyError:
                    error_code = -5
                    error_msg = (
                        "Bad resource SQL constraints request:"
                        + sql_constraints
                        + "\n"
                        + "SQLAlchemyError: "
                        + str(exc)
                    )
                    error = (error_code, error_msg)
                    return (error, None, None)

                roids = [resource_set.rid_i2o[int(y[0])] for y in request_constraints]
                constraints = ProcSet(*roids)

            hy_levels = []
            hy_nbs = []
            for resource_value in resource_value_lst:
                res_name = resource_value["resource"]
                if res_name not in resource_set.hierarchy:
                    possible_options = ", ".join(resource_set.hierarchy.keys())
                    error_code = -3
                    error_msg = (
                        f"Bad resources name: {res_name} is not a valid resources name."
                        f"Valid resource names are: {possible_options}"
                    )
                    error = (error_code, error_msg)
                    return (error, None, None)

                value = resource_value["value"]
                hy_levels.append(resource_set.hierarchy[res_name])
                hy_nbs.append(int(value))

            cts_resources_itvs = constraints & resources_itvs

            for soc in resource_set.hierarchy['cpu']:
                avail_cores = soc & cts_resources_itvs
                cts_resources_itvs -= ProcSet(*avail_cores[int(len(soc)/2):len(soc)])

            res_itvs = find_resource_hierarchies_scattered(
                cts_resources_itvs, hy_levels, hy_nbs
            )
            if res_itvs:
                estimated_nb_res += len(res_itvs)
                # break

        if estimated_nb_res > 0:
            is_resource_available = True

        estimated_nb_resources.append((estimated_nb_res, walltime))

    if not is_resource_available:
        error = (-5, "There are not enough resources for your request")
        return (error, None, None)

    return ((0, ""), is_resource_available, estimated_nb_resources)


if 'spread' in types:
    types = list(map(lambda t: t.replace('spread','find=spread'),types))

    import oar.lib.globals
    import sqlalchemy.orm

    engine = oar.lib.globals.init_db(config)

    session_factory = sqlalchemy.orm.sessionmaker(bind=engine)
    scoped = sqlalchemy.orm.scoped_session(session_factory)
    session = scoped()

    if estimate_job_nb_resources_in_spread(session, config, resource_request, properties)[0][0] < 0:
        raise Exception("# ADMISSION RULE> There are not enough resources for your request using the spread method")
