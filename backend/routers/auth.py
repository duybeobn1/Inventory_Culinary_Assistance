from fastapi import APIRouter, HTTPException, Depends, status
from schema import SignUpRequest, SignInRequest, AuthResponse, ProfileResponse, ProfileUpdate, SaveRecipeRequest, UpdateRecipeRequest
from dependencies import get_current_user
from db.supabase import supabase
from services.auth_service import create_profile, get_profile_by_user_id, update_profile, get_user_recipes, save_recipe, update_recipe, delete_recipe
from logging_config import logger

router = APIRouter(tags=["Auth"])


@router.post("/api/auth/signup", response_model=AuthResponse)
async def signup(request: SignUpRequest):
    try:
        user = supabase.auth.sign_up(
            {"email": request.email, "password": request.password}
        )

        if not user.user:
            raise HTTPException(status_code=400, detail="Signup failed")

        user_id = user.user.id
        email = user.user.email or request.email

        token = user.session.access_token if user.session else ""

        create_profile(user_id, display_name=request.display_name)

        logger.info(f"User signed up: {email}")

        return AuthResponse(
            status="success",
            user_id=user_id,
            email=email,
            access_token=token,
            display_name=request.display_name,
        )

    except Exception as e:
        error_msg = str(e)
        if "User already registered" in error_msg:
            raise HTTPException(status_code=409, detail="Email already registered")
        logger.error(f"Signup failed: {e}")
        raise HTTPException(status_code=400, detail=error_msg)


@router.post("/api/auth/signin", response_model=AuthResponse)
async def signin(request: SignInRequest):
    try:
        user = supabase.auth.sign_in_with_password(
            {"email": request.email, "password": request.password}
        )

        if not user.user:
            raise HTTPException(status_code=401, detail="Invalid credentials")

        user_id = user.user.id
        email = user.user.email or request.email
        token = user.session.access_token

        profile = get_profile_by_user_id(user_id)
        display_name = profile.get("display_name") if profile else None

        logger.info(f"User signed in: {email}")

        return AuthResponse(
            status="success",
            user_id=user_id,
            email=email,
            access_token=token,
            display_name=display_name,
        )

    except Exception as e:
        error_msg = str(e)
        if "Invalid login credentials" in error_msg:
            raise HTTPException(status_code=401, detail="Invalid email or password")
        logger.error(f"Signin failed: {e}")
        raise HTTPException(status_code=401, detail="Invalid credentials")


@router.get("/api/auth/me", response_model=ProfileResponse)
async def get_my_profile(user_id: str = Depends(get_current_user)):
    profile = get_profile_by_user_id(user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    return ProfileResponse(
        id=profile["id"],
        user_id=profile["user_id"],
        display_name=profile.get("display_name"),
        avatar_url=profile.get("avatar_url"),
        preferences=profile.get("preferences", {}),
        created_at=profile.get("created_at", ""),
    )


@router.put("/api/auth/profile")
async def update_my_profile(
    updates: ProfileUpdate,
    user_id: str = Depends(get_current_user),
):
    update_data = updates.model_dump(exclude_none=True)
    if not update_data:
        return {"status": "success", "message": "Nothing to update"}

    result = update_profile(user_id, update_data)
    if not result:
        raise HTTPException(status_code=500, detail="Failed to update profile")

    return {"status": "success", "profile": result}


@router.get("/api/auth/recipes")
async def list_my_recipes(
    favorites_only: bool = False,
    user_id: str = Depends(get_current_user),
):
    recipes = get_user_recipes(user_id, favorites_only=favorites_only)
    return {"status": "success", "recipes": recipes}


@router.post("/api/auth/recipes")
async def create_recipe(
    request: SaveRecipeRequest,
    user_id: str = Depends(get_current_user),
):
    result = save_recipe(
        user_id,
        recipe_name=request.recipe_name,
        recipe_data=request.recipe_data,
        is_favorite=request.is_favorite,
    )
    if not result:
        raise HTTPException(status_code=500, detail="Failed to save recipe")
    return {"status": "success", "recipe_id": result["id"]}


@router.put("/api/auth/recipes/{recipe_id}")
async def update_my_recipe(
    recipe_id: str,
    request: UpdateRecipeRequest,
    user_id: str = Depends(get_current_user),
):
    result = update_recipe(
        recipe_id,
        user_id,
        recipe_name=request.recipe_name,
        recipe_data=request.recipe_data,
        is_favorite=request.is_favorite,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Recipe not found or access denied")
    return {"status": "success", "recipe": result}


@router.delete("/api/auth/recipes/{recipe_id}")
async def delete_my_recipe(
    recipe_id: str,
    user_id: str = Depends(get_current_user),
):
    ok = delete_recipe(recipe_id, user_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Recipe not found or access denied")
    return {"status": "success", "message": "Recipe deleted"}
